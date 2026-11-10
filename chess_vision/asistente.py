import os
import glob
import time
import threading
import cv2
import numpy as np
import chess
import chess.engine
from chess_vision.analisis.mentor_ajedrez import explicar_jugada
from chess_vision.captura.tablero import TableroDetector
from chess_vision.rutas import PLANTILLAS_PIEZAS, RAIZ_PROYECTO, STOCKFISH_CONFIG, ruta_local

CANON_SIZE = 64


def obtener_ruta_stockfish():
    config = ruta_local(STOCKFISH_CONFIG)
    if not config.is_file():
        raise FileNotFoundError("No se encontró stockfish_path.txt. Ejecuta primero 'python -m chess_vision.herramientas.descargar_stockfish'.")
    with config.open(encoding="utf-8") as f:
        ruta = f.read().strip()
    return os.path.normpath(os.path.join(RAIZ_PROYECTO, ruta)) if ruta else ruta


class AnalisisResultado:
    def __init__(self, move=None, eval_str="N/A", mate_in=None, pv_moves=None, idea="", is_mate_for_white=None, score_obj=None):
        self.move = move
        self.eval_str = eval_str
        self.mate_in = mate_in
        self.pv_moves = pv_moves or []
        self.idea = idea
        self.is_mate_for_white = is_mate_for_white
        self.score_obj = score_obj

    def __iter__(self):
        # Permite unpacking tradicional compatible con: best_move, eval_str = resultado
        return iter((self.move, self.eval_str))

    def __getitem__(self, key):
        return getattr(self, key)


def limpiar_fondo(gray):
    """
    Neutraliza cualquier color de fondo del tablero (casilla clara, casilla oscura,
    resaltado amarillo o verde de última jugada), preservando únicamente el cuerpo
    blanco (>238), el cuerpo gris oscuro (<105) y los contornos negros de la pieza.
    """
    clean = gray.astype(np.float32)
    mask_bg = (gray >= 105) & (gray <= 238)
    clean[mask_bg] = 170.0
    return clean


class AsistenteAjedrez:
    def __init__(self, orientacion_blancas=True):
        self.orientacion_blancas = orientacion_blancas
        self.detector = TableroDetector()
        self.stockfish_path = obtener_ruta_stockfish()
        self.templates = self._cargar_plantillas()

        # Proceso persistente de Stockfish con bloqueo para hilos
        self.engine_lock = threading.Lock()
        self.engine = None
        self._iniciar_motor()

    def _iniciar_motor(self):
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        except Exception as e:
            print(f"[!] Error al iniciar Stockfish: {e}")
            self.engine = None

    def asegurar_motor(self):
        """Verifica que el motor esté vivo y respondiendo; si no, lo relanza automáticamente."""
        if self.engine is None:
            self._iniciar_motor()
            return self.engine
        try:
            self.engine.ping()
        except Exception:
            try:
                self.engine.close()
            except Exception:
                pass
            self.engine = None
            self._iniciar_motor()
        return self.engine

    def cerrar(self):
        with self.engine_lock:
            try:
                if self.engine:
                    self.engine.quit()
            except Exception:
                pass

    def _cargar_plantillas(self):
        carpeta_piezas = ruta_local(PLANTILLAS_PIEZAS)
        archivos = sorted(glob.glob(os.path.join(carpeta_piezas, "*.png")))
        if not archivos:
            raise FileNotFoundError(
                f"No hay piezas en '{carpeta_piezas}'. Ejecuta 'python -m chess_vision.herramientas.aprender_piezas' con el tablero en posición inicial."
            )

        # Usar las plantillas capturadas directamente del tablero (sin necesidad de duplicar clara/oscura
        # ya que limpiar_fondo elimina por completo el fondo de la casilla)
        preferidas = [
            "blanca_pieza_P_clara.png", "blanca_pieza_N_clara.png", "blanca_pieza_B_clara.png",
            "blanca_pieza_R_clara.png", "blanca_pieza_Q_clara.png", "blanca_pieza_K_oscura.png",
            "negra_pieza_p_clara.png", "negra_pieza_n_clara.png", "negra_pieza_b_clara.png",
            "negra_pieza_r_oscura.png", "negra_pieza_q_oscura.png", "negra_pieza_k_clara.png"
        ]

        rutas_a_cargar = []
        for fn in preferidas:
            p = os.path.join(carpeta_piezas, fn)
            if os.path.exists(p):
                rutas_a_cargar.append(p)

        if len(rutas_a_cargar) < 12:
            rutas_a_cargar = [p for p in archivos if "empty" not in os.path.basename(p)]

        templates = []
        margin = 6
        for path in rutas_a_cargar:
            nombre = os.path.splitext(os.path.basename(path))[0]
            partes = nombre.split("_")
            pieza = partes[2] if (len(partes) >= 4 and partes[1] == "pieza") else partes[0]

            img = cv2.imread(path)
            if img is None:
                continue
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            t_res = cv2.resize(gray, (CANON_SIZE, CANON_SIZE), interpolation=cv2.INTER_AREA)
            clean_t = limpiar_fondo(t_res)
            crop = clean_t[margin:CANON_SIZE - margin, margin:CANON_SIZE - margin]

            templates.append({
                "nombre": nombre,
                "pieza": pieza,
                "is_white": pieza.isupper(),
                "crop": crop
            })
        return templates

    def clasificar_casilla(self, img_casilla, es_clara=True):
        gray_raw = cv2.cvtColor(img_casilla, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray_raw, (CANON_SIZE, CANON_SIZE), interpolation=cv2.INTER_AREA)

        # 1. Región central (40x40) para detectar si hay pieza y de qué color es
        center = gray[12:52, 12:52]
        c_size = 1600.0

        ratio_dark = np.count_nonzero(center < 95) / c_size
        ratio_bright = np.count_nonzero(center > 238) / c_size

        # Si no hay ni relleno oscuro ni relleno blanco, la casilla está vacía
        if ratio_dark < 0.04 and ratio_bright < 0.05:
            return "empty"

        # 2. Determinar bando (Blanca vs Negra)
        es_blanca = ratio_bright >= 0.06

        # 3. Correlación normalizada deslizante con fondo neutralizado
        # Inmune a desfases de calibración y a cualquier color de casilla
        clean_sq = limpiar_fondo(gray)
        pad = 5
        clean_pad = np.full((CANON_SIZE + 2 * pad, CANON_SIZE + 2 * pad), 170.0, dtype=np.float32)
        clean_pad[pad:pad + CANON_SIZE, pad:pad + CANON_SIZE] = clean_sq

        best_char = "P" if es_blanca else "p"
        best_score = -1.0

        for item in self.templates:
            if item["is_white"] != es_blanca:
                continue
            res = cv2.matchTemplate(clean_pad, item["crop"], cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            if score > best_score:
                best_score = score
                best_char = item["pieza"]

        return best_char

    def generar_fen(self, casillas, turno="w"):
        columnas = ["a", "b", "c", "d", "e", "f", "g", "h"]
        filas = ["8", "7", "6", "5", "4", "3", "2", "1"]

        filas_fen = []
        tablero_matriz = []

        for r_idx, fila in enumerate(filas):
            fila_str = ""
            fila_visual = []
            vacias = 0
            for c_idx, col in enumerate(columnas):
                nombre_casilla = f"{col}{fila}"
                img_casilla = casillas[nombre_casilla]
                es_clara = (c_idx + r_idx) % 2 == 0

                pieza = self.clasificar_casilla(img_casilla, es_clara)

                if pieza == "empty":
                    vacias += 1
                    fila_visual.append(".")
                else:
                    if vacias > 0:
                        fila_str += str(vacias)
                        vacias = 0
                    fila_str += pieza
                    fila_visual.append(pieza)

            if vacias > 0:
                fila_str += str(vacias)
            filas_fen.append(fila_str)
            tablero_matriz.append(" ".join(fila_visual))

        cuerpo_fen = "/".join(filas_fen)
        fen_completo = f"{cuerpo_fen} {turno} - - 0 1"
        return fen_completo, tablero_matriz

    def obtener_mejor_jugada(self, fen, tiempo_analisis=0.3):
        try:
            board = chess.Board(fen)
        except Exception as e:
            return None, f"Error en FEN: {e}"

        if board.king(chess.WHITE) is None:
            return None, "Falta Rey Blanco"
        if board.king(chess.BLACK) is None:
            return None, "Falta Rey Negro"

        # Validación vital de legalidad
        if not board.is_valid():
            return None, "Posición en transición"

        # Fin de partida
        if board.is_checkmate():
            return AnalisisResultado(None, "¡JAQUE MATE!", None, [], "Partida finalizada por jaque mate")
        if board.is_stalemate():
            return AnalisisResultado(None, "Tablas (Ahogado)", None, [], "Partida en tablas por rey ahogado")

        try:
            with self.engine_lock:
                motor = self.asegurar_motor()
                if not motor:
                    return AnalisisResultado(None, "Motor no disponible", None, [], "")

                info = motor.analyse(board, chess.engine.Limit(time=tiempo_analisis))
                pv_list = info.get("pv", [])
                best_move = pv_list[0] if pv_list else None
                if not best_move:
                    result = motor.play(board, chess.engine.Limit(time=0.08))
                    best_move = result.move

                score = info.get("score")
                eval_str = "0.00"
                mate_in = None
                is_mate_for_white = None

                if score and score.is_mate():
                    m_val = score.white().mate()
                    if m_val is not None:
                        mate_in = abs(m_val)
                        is_mate_for_white = (m_val > 0)
                        eval_str = f"#{m_val:+d}"
                elif score:
                    cp = score.white().score() or 0
                    eval_str = f"{cp / 100.0:+.2f}"

                pv_moves = pv_list[:5]
                idea = explicar_jugada(board, best_move) if best_move else ""

                return AnalisisResultado(
                    move=best_move,
                    eval_str=eval_str,
                    mate_in=mate_in,
                    pv_moves=pv_moves,
                    idea=idea,
                    is_mate_for_white=is_mate_for_white,
                    score_obj=score
                )
        except Exception:
            with self.engine_lock:
                try:
                    if self.engine:
                        self.engine.close()
                except Exception:
                    pass
                self.engine = None
                self._iniciar_motor()
            return AnalisisResultado(None, "Calculando...", None, [], "")

    @property
    def estado_tracker(self):
        return self.detector.estado_tracker

    def analizar_pantalla(self, turno="w"):
        casillas, tablero_img = self.detector.obtener_casillas(orientacion_blancas=self.orientacion_blancas)
        if casillas is None:
            return None, None, None, "Buscando tablero..."
        fen, matriz = self.generar_fen(casillas, turno=turno)
        jugada, eval_score = self.obtener_mejor_jugada(fen)
        return fen, matriz, jugada, eval_score
