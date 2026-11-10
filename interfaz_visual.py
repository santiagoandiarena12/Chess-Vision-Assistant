import os
import sys
import time
import math
import ctypes
import threading
import textwrap
from queue import Empty, SimpleQueue
import pygame
import chess
import chess.engine
import cv2
import numpy as np
from asistente import AsistenteAjedrez, obtener_ruta_stockfish
from evaluador_simulacion import EvaluadorSimulacion, SimulacionResultado
from mentor_ajedrez import explicar_jugada
from monitor_raton_ajedrez import MonitorRatonAjedrez
from revision_pgn import SesionRevision, cargar_partida, evaluar_alternativa, preparar_alternativas, revisar_partida

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PIEZAS_DIR = os.path.join(BASE_DIR, "piezas_hd")

COLOR_BG = (28, 30, 36)
COLOR_PANEL = (38, 41, 49)
COLOR_CARD = (49, 53, 64)
COLOR_TEXT_MAIN = (240, 240, 245)
COLOR_TEXT_MUTED = (160, 165, 178)
COLOR_ACCENT = (78, 172, 80)
COLOR_ACCENT_HOVER = (98, 192, 100)
COLOR_WAITING = (220, 160, 50)
COLOR_BTN_HOVER = (60, 65, 78)

COLOR_SQ_LIGHT = (238, 238, 210)
COLOR_SQ_DARK = (118, 150, 86)
COLOR_HIGHLIGHT = (246, 238, 90, 140)
COLOR_ARROW = (46, 204, 113)

class VisualChessApp:
    def __init__(self, juego_con_blancas=None):
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("Chess Vision Assistant - En Vivo")
        
        self.win_width = 980
        self.win_height = 640
        self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        
        self._set_always_on_top()

        self.font_title = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self.font_bold = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_regular = pygame.font.SysFont("Segoe UI", 14)
        self.font_small = pygame.font.SysFont("Segoe UI", 11)
        self.font_move = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_eval = pygame.font.SysFont("Segoe UI", 11, bold=True)
        self.font_btn = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_idea = pygame.font.SysFont("Segoe UI", 12, italic=True)
        self.font_victory = pygame.font.SysFont("Segoe UI", 24, bold=True)
        self.font_victory_sub = pygame.font.SysFont("Segoe UI", 13)
        self.font_ghost = pygame.font.SysFont("Segoe UI", 11, bold=True)
        self.font_mate = pygame.font.SysFont("Segoe UI", 12, bold=True)

        self.raw_piece_images = self._load_raw_pieces()
        self.scaled_piece_images = {}

        # Botones y coordenadas interactivas
        self.mouse_pos = (0, 0)
        self.btn_blancas_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_negras_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_cambiar_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_reset_game_rect = pygame.Rect(0, 0, 0, 0)
        self.pgn_trabajo = None
        self.ghost_pill_rects = []
        self.ghost_step = 0
        self.current_cursor = pygame.SYSTEM_CURSOR_ARROW

        # Estado de la App: "SELECCIONANDO" o "JUGANDO"
        if juego_con_blancas is None:
            self.estado_app = "SELECCIONANDO"
            self.juego_con_blancas = True
            self.mi_color_str = "w"
            flip_inicial = False
            status_inicial = "Esperando elección de bando..."
            turn_name_inicial = "Elige tu bando"
        else:
            self.estado_app = "JUGANDO"
            self.juego_con_blancas = juego_con_blancas
            self.mi_color_str = "w" if self.juego_con_blancas else "b"
            flip_inicial = not self.juego_con_blancas
            status_inicial = "Escaneando..."
            turn_name_inicial = "¡TU TURNO!" if self.juego_con_blancas else "Rival pensando..."

        self._recalcular_dimensiones()
        self.scaled_piece_images = self._scale_piece_images()

        self.state = {
            "board": chess.Board(),
            "best_move": None,
            "eval_str": "0.0",
            "eval_score": 0.0,
            "last_move": None,
            "turno_actual": "w",
            "es_mi_turno": (self.juego_con_blancas if self.estado_app == "JUGANDO" else False),
            "turn_name": turn_name_inicial,
            "move_history": [],
            "status": status_inicial,
            "tracker_status": "BUSCANDO",
            "flip": flip_inicial,
            "pv_moves": [],
            "mentor_idea": "",
            "mate_in": None,
            "game_over": None,
            "game_over_subtitle": "",
            "simulacion_activa": False,
            "simulacion_res": None,
            "simulacion_orig_sq": None,
            "simulacion_curr_sq": None,
            "flechas_visuales": []
        }
        self.state_lock = threading.Lock()
        
        self.current_eval_visual = 0.0
        self.running = True
        self.asistente = None
        self.evaluador_simulacion = None
        self.monitor_raton = None

        self.worker_thread = threading.Thread(target=self._background_vision_loop, daemon=True)
        self.worker_thread.start()

        self.sim_thread = threading.Thread(target=self._simulacion_worker_loop, daemon=True)
        self.sim_thread.start()

    def _recalcular_dimensiones(self):
        self.board_size = max(240, min(self.win_height - 80, self.win_width - 320))
        self.square_size = self.board_size // 8
        self.eval_bar_width = 24
        self.panel_x = 50 + self.eval_bar_width + self.board_size + 20
        self.panel_width = max(220, self.win_width - self.panel_x - 20)

        # Posicionamiento de botones en el panel
        px = self.panel_x
        pw = self.panel_width
        py = 40
        btn_w = pw - 48
        btn_h = 46

        self.btn_blancas_rect = pygame.Rect(px + 24, py + 130, btn_w, btn_h)
        self.btn_negras_rect = pygame.Rect(px + 24, py + 190, btn_w, btn_h)
        self.btn_cambiar_rect = pygame.Rect(px + pw - 135, py + self.board_size - 32, 120, 24)
        self.btn_abrir_pgn_rect = pygame.Rect(px + 16, py + self.board_size + 6, pw - 32, 28)

    def _actualizar_cursor_raton(self):
        hover_boton = False
        if self.estado_app == "SELECCIONANDO":
            hover_boton = (self.btn_blancas_rect.collidepoint(self.mouse_pos) or 
                           self.btn_negras_rect.collidepoint(self.mouse_pos) or
                           self.btn_abrir_pgn_rect.collidepoint(self.mouse_pos))
        elif self.estado_app == "REVISION_PGN":
            hover_boton = any(rect.collidepoint(self.mouse_pos) for _, rect in self.pgn_controles)
        elif self.estado_app == "JUGANDO":
            if self.btn_cambiar_rect.collidepoint(self.mouse_pos):
                hover_boton = True
            elif self.state.get("game_over") and self.btn_reset_game_rect.collidepoint(self.mouse_pos):
                hover_boton = True
            else:
                for _, p_rect in self.ghost_pill_rects:
                    if p_rect.collidepoint(self.mouse_pos):
                        hover_boton = True
                        break

        target_cursor = pygame.SYSTEM_CURSOR_HAND if hover_boton else pygame.SYSTEM_CURSOR_ARROW
        if getattr(self, "current_cursor", None) != target_cursor:
            self.current_cursor = target_cursor
            try:
                pygame.mouse.set_cursor(target_cursor)
            except Exception:
                pass

    def _set_always_on_top(self):
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
        except Exception:
            pass

    def _load_raw_pieces(self):
        raw = {}
        for p in ["wK", "wQ", "wR", "wB", "wN", "wP", "bK", "bQ", "bR", "bB", "bN", "bP"]:
            path = os.path.join(PIEZAS_DIR, f"{p}.png")
            if os.path.exists(path):
                raw[p] = pygame.image.load(path).convert_alpha()
        return raw

    def _scale_piece_images(self):
        scaled = {}
        for k, img in self.raw_piece_images.items():
            scaled[k] = pygame.transform.smoothscale(img, (self.square_size, self.square_size))
        return scaled

    def seleccionar_bando(self, es_blancas):
        self.juego_con_blancas = es_blancas
        self.mi_color_str = "w" if es_blancas else "b"
        self.estado_app = "JUGANDO"
        self.ghost_step = 0
        
        with self.state_lock:
            self.state["flip"] = not es_blancas
            self.state["board"] = chess.Board()
            self.state["turno_actual"] = "w"
            self.state["es_mi_turno"] = es_blancas
            self.state["turn_name"] = "¡TU TURNO!" if es_blancas else "Rival pensando..."
            self.state["status"] = "En Vivo"
            self.state["best_move"] = None
            self.state["last_move"] = None
            self.state["move_history"] = []
            self.state["pv_moves"] = []
            self.state["mentor_idea"] = ""
            self.state["mate_in"] = None
            self.state["game_over"] = None
            self.state["game_over_subtitle"] = ""

        if self.asistente:
            self.asistente.orientacion_blancas = es_blancas

    def volver_a_seleccion(self):
        self.estado_app = "SELECCIONANDO"
        self.ghost_step = 0
        with self.state_lock:
            self.state["status"] = "Esperando elección de bando..."
            self.state["turn_name"] = "Elige tu bando"
            self.state["best_move"] = None
            self.state["es_mi_turno"] = False
            self.state["pv_moves"] = []
            self.state["mentor_idea"] = ""
            self.state["mate_in"] = None
            self.state["game_over"] = None
            self.state["game_over_subtitle"] = ""

    def nueva_partida(self):
        self.ghost_step = 0
        with self.state_lock:
            self.state["board"] = chess.Board()
            self.state["turno_actual"] = "w"
            self.state["es_mi_turno"] = self.juego_con_blancas
            self.state["turn_name"] = "¡TU TURNO!" if self.juego_con_blancas else "Rival pensando..."
            self.state["status"] = "En Vivo"
            self.state["best_move"] = None
            self.state["last_move"] = None
            self.state["move_history"] = []
            self.state["pv_moves"] = []
            self.state["mentor_idea"] = ""
            self.state["mate_in"] = None
            self.state["game_over"] = None
            self.state["game_over_subtitle"] = ""
            self.state["simulacion_activa"] = False
            self.state["simulacion_res"] = None
            self.state["simulacion_orig_sq"] = None
            self.state["simulacion_curr_sq"] = None

    def _simulacion_worker_loop(self):
        last_eval_key = None
        while self.running:
            time.sleep(0.025)
            if self.estado_app != "JUGANDO":
                continue

            active = False
            orig_sq = None
            dest_sq = None
            candidate_move = None
            is_drawing_only = False
            drawing_orig = None

            # 1. Prioridad: flecha detectada por el monitor del ratón (click derecho en vivo)
            if self.monitor_raton:
                estado = self.monitor_raton.obtener_estado()
                if estado["active"] and estado["orig_sq"] and estado["dest_sq"]:
                    active = True
                    orig_sq = estado["orig_sq"]
                    dest_sq = estado["dest_sq"]
                    candidate_move = estado["candidate_move"]
                elif estado.get("is_drawing") and estado.get("drawing_orig"):
                    is_drawing_only = True
                    drawing_orig = estado.get("drawing_orig")

            # 2. Respaldo: flechas visuales naranjas detectadas directamente en la pantalla
            if not active and not is_drawing_only:
                with self.state_lock:
                    flechas_vis = self.state.get("flechas_visuales", [])
                if flechas_vis:
                    active = True
                    orig_sq, dest_sq, candidate_move = flechas_vis[0]

            if active and orig_sq and dest_sq:
                with self.state_lock:
                    tablero_publicado = self.state["board"]
                    board_actual = tablero_publicado.copy()
                    eval_actual = self.state.get("eval_str", "0.0")
                    best_m = self.state.get("best_move")
                    best_score = self.state.get("best_score_obj")

                if not candidate_move:
                    try:
                        orig_idx = chess.parse_square(orig_sq)
                        dest_idx = chess.parse_square(dest_sq)
                        candidate_move = chess.Move(orig_idx, dest_idx)
                    except Exception:
                        candidate_move = None

                if candidate_move:
                    eval_key = (board_actual.fen(), candidate_move.uci())
                    if eval_key != last_eval_key:
                        last_eval_key = eval_key
                        res_eval = None
                        if self.evaluador_simulacion:
                            res_eval = self.evaluador_simulacion.evaluar_candidata(
                                board=board_actual,
                                move=candidate_move,
                                best_move=best_m,
                                best_score_obj=best_score,
                                eval_optima_str=eval_actual,
                                tiempo_analisis=0.15
                            )

                        with self.state_lock:
                            if self.state["board"] is not tablero_publicado:
                                last_eval_key = None
                                continue
                            self.state["simulacion_activa"] = True
                            self.state["simulacion_res"] = res_eval
                            self.state["simulacion_orig_sq"] = orig_sq
                            self.state["simulacion_curr_sq"] = dest_sq
            elif is_drawing_only and drawing_orig:
                last_eval_key = None
                with self.state_lock:
                    self.state["simulacion_activa"] = True
                    self.state["simulacion_res"] = None
                    self.state["simulacion_orig_sq"] = drawing_orig
                    self.state["simulacion_curr_sq"] = None
            else:
                last_eval_key = None
                if self.state.get("simulacion_activa"):
                    with self.state_lock:
                        self.state["simulacion_activa"] = False
                        self.state["simulacion_res"] = None
                        self.state["simulacion_orig_sq"] = None
                        self.state["simulacion_curr_sq"] = None

    def _detectar_resalte_ultima_jugada(self, img_tablero, orientacion_blancas):
        """
        Detecta las casillas con el resalte amarillo característico de Chess.com.
        Retorna lista de nombres de casillas con resalte (ej: ['d8', 'h4']) o [].
        """
        if img_tablero is None:
            return []
        h, w = img_tablero.shape[:2]
        sq_w, sq_h = w / 8.0, h / 8.0
        cols = ['a','b','c','d','e','f','g','h'] if orientacion_blancas else ['h','g','f','e','d','c','b','a']
        fils = ['8','7','6','5','4','3','2','1'] if orientacion_blancas else ['1','2','3','4','5','6','7','8']

        amarillas = []
        for r in range(8):
            for c in range(8):
                cell = img_tablero[int(r*sq_h):int((r+1)*sq_h), int(c*sq_w):int((c+1)*sq_w)]
                if cell.shape[0] < 20 or cell.shape[1] < 20:
                    continue
                # Revisar las 4 esquinas de la casilla (lejos de la pieza en el centro)
                corners = [cell[:12, :12], cell[:12, -12:], cell[-12:, :12], cell[-12:, -12:]]
                mean_bgr = np.mean([np.mean(cr, axis=(0,1)) for cr in corners], axis=0)
                b, g, r_val = mean_bgr
                ratio_rb = r_val / max(1.0, b)
                # El amarillo de Chess.com en casillas claras/oscuras tiene R/B > 1.60 y alto G, R (> 165)
                if ratio_rb > 1.60 and g > 165 and r_val > 165:
                    amarillas.append(f"{cols[c]}{fils[r]}")

        return amarillas

    def _detectar_flechas_visuales(self, img_tablero, orientacion_blancas, board):
        """
        Detecta flechas naranjas trazadas en Chess.com directamente desde la imagen capturada.
        Soporta movimientos rectos, diagonales y en 'L' (caballos), resolviendo los extremos reales.
        Retorna lista de tuplas (sq_orig, sq_dest, move).
        """
        if img_tablero is None or board is None:
            return []
        h, w = img_tablero.shape[:2]
        sq_w, sq_h = w / 8.0, h / 8.0
        cols = ['a','b','c','d','e','f','g','h'] if orientacion_blancas else ['h','g','f','e','d','c','b','a']
        fils = ['8','7','6','5','4','3','2','1'] if orientacion_blancas else ['1','2','3','4','5','6','7','8']

        def pt_a_casilla(px, py):
            c_idx = int(np.clip(px / sq_w, 0, 7))
            r_idx = int(np.clip(py / sq_h, 0, 7))
            return f'{cols[c_idx]}{fils[r_idx]}'

        # Máscara de flecha naranja Chess.com (BGR: B < 110, G 140-225, R > 200)
        mask = ((img_tablero[:,:,0] < 110) & (img_tablero[:,:,1] > 140) & (img_tablero[:,:,1] < 225) & (img_tablero[:,:,2] > 200)).astype(np.uint8) * 255
        if np.sum(mask) < 200:
            return []

        # Cerrado morfológico para conectar tramos de flechas cortados por piezas o peones
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
        closed_mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        flechas = []
        color_jugador = chess.WHITE if orientacion_blancas else chess.BLACK

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 280:
                pts = cnt[:, 0, :]  # x, y
                if len(pts) < 4:
                    continue

                # 1. Encontrar los dos puntos extremos de la flecha (diámetro del contorno)
                dists = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=2)
                i1, i2 = np.unravel_index(np.argmax(dists), dists.shape)
                sq_a = pt_a_casilla(pts[i1][0], pts[i1][1])
                sq_b = pt_a_casilla(pts[i2][0], pts[i2][1])

                # 2. Casillas que toca el contorno
                m_cnt = np.zeros(closed_mask.shape, dtype=np.uint8)
                cv2.drawContours(m_cnt, [cnt], -1, 255, -1)
                sqs_tocadas = set([sq_a, sq_b])
                for r_i in range(8):
                    for c_i in range(8):
                        sub = m_cnt[int(r_i*sq_h):int((r_i+1)*sq_h), int(c_i*sq_w):int((c_i+1)*sq_w)]
                        if np.count_nonzero(sub) > 40:
                            sqs_tocadas.add(f'{cols[c_i]}{fils[r_i]}')

                par_encontrado = None

                # Prioridad 1: Conexión legal directa entre los extremos sq_a y sq_b
                for orig, dest in [(sq_a, sq_b), (sq_b, sq_a)]:
                    p = board.piece_at(chess.parse_square(orig))
                    if p and p.color == color_jugador:
                        promo = None
                        if p.piece_type == chess.PAWN:
                            tr = chess.square_rank(chess.parse_square(dest))
                            if (p.color == chess.WHITE and tr == 7) or (p.color == chess.BLACK and tr == 0):
                                promo = chess.QUEEN
                        m = chess.Move(chess.parse_square(orig), chess.parse_square(dest), promotion=promo)
                        if m in board.legal_moves:
                            par_encontrado = (orig, dest, m)
                            break

                # Prioridad 2: Punta en un extremo (sq_a o sq_b) y origen en casilla tocada con pieza
                if not par_encontrado:
                    for dest in [sq_b, sq_a]:
                        for orig in sqs_tocadas:
                            if orig != dest:
                                p = board.piece_at(chess.parse_square(orig))
                                if p and p.color == color_jugador:
                                    promo = None
                                    if p.piece_type == chess.PAWN:
                                        tr = chess.square_rank(chess.parse_square(dest))
                                        if (p.color == chess.WHITE and tr == 7) or (p.color == chess.BLACK and tr == 0):
                                            promo = chess.QUEEN
                                    m = chess.Move(chess.parse_square(orig), chess.parse_square(dest), promotion=promo)
                                    if m in board.legal_moves:
                                        par_encontrado = (orig, dest, m)
                                        break
                        if par_encontrado:
                            break

                # Prioridad 3: Cualquier jugada legal entre casillas tocadas (favoreciendo la mayor distancia / alcance)
                if not par_encontrado:
                    max_d = -1
                    for orig in sqs_tocadas:
                        p = board.piece_at(chess.parse_square(orig))
                        if p and p.color == color_jugador:
                            for dest in sqs_tocadas:
                                if orig != dest:
                                    promo = None
                                    if p.piece_type == chess.PAWN:
                                        tr = chess.square_rank(chess.parse_square(dest))
                                        if (p.color == chess.WHITE and tr == 7) or (p.color == chess.BLACK and tr == 0):
                                            promo = chess.QUEEN
                                    m = chess.Move(chess.parse_square(orig), chess.parse_square(dest), promotion=promo)
                                    if m in board.legal_moves:
                                        d = abs(chess.square_file(chess.parse_square(orig)) - chess.square_file(chess.parse_square(dest))) + abs(chess.square_rank(chess.parse_square(orig)) - chess.square_rank(chess.parse_square(dest)))
                                        if d > max_d:
                                            max_d = d
                                            par_encontrado = (orig, dest, m)

                # Prioridad 4: Fallback para jugadas no legales (análisis de jugadas ilegales/clavadas)
                if not par_encontrado:
                    p_a = board.piece_at(chess.parse_square(sq_a))
                    p_b = board.piece_at(chess.parse_square(sq_b))
                    if p_a and p_a.color == color_jugador:
                        m = chess.Move(chess.parse_square(sq_a), chess.parse_square(sq_b))
                        par_encontrado = (sq_a, sq_b, m)
                    elif p_b and p_b.color == color_jugador:
                        m = chess.Move(chess.parse_square(sq_b), chess.parse_square(sq_a))
                        par_encontrado = (sq_b, sq_a, m)

                if par_encontrado:
                    flechas.append(par_encontrado)

        return flechas

    def _resolver_posicion(self, tablero, anterior, piezas_vistas, resaltes):
        cuerpo = tablero.board_fen()
        if anterior is not None:
            if cuerpo == anterior.board_fen():
                return anterior, None

            # Reproducir la jugada observada conserva turno, enroques y captura al paso.
            candidato = anterior.copy(stack=False)
            for jugada in anterior.legal_moves:
                candidato.push(jugada)
                if candidato.board_fen() == cuerpo:
                    origen = chess.square_name(jugada.from_square).upper()
                    destino = chess.square_name(jugada.to_square).upper()
                    return candidato, f"{origen} → {destino}"
                candidato.pop()

        if cuerpo == chess.STARTING_BOARD_FEN:
            return chess.Board(), None

        # Al enganchar una partida en curso, inferir el turno desde lo visible.
        origen = destino = None
        if 1 <= len(resaltes) <= 2:
            destino = next((sq for sq in resaltes if piezas_vistas[sq] != "empty"), None)
            origen = next((sq for sq in resaltes if piezas_vistas[sq] == "empty"), None)

        if destino is None and anterior is not None:
            for sq, pieza in piezas_vistas.items():
                previa = anterior.piece_at(chess.parse_square(sq))
                if pieza == "empty" and previa:
                    origen = origen or sq
                elif pieza != "empty" and (previa is None or previa.symbol() != pieza):
                    destino = destino or sq

        tablero.turn = chess.WHITE if destino is None else piezas_vistas[destino].islower()
        if tablero.status() & chess.STATUS_OPPOSITE_CHECK:
            tablero.turn = not tablero.turn

        jugada_str = f"{origen.upper()} → {destino.upper()}" if origen and destino else None
        return tablero, jugada_str

    def _background_vision_loop(self):
        try:
            self.asistente = AsistenteAjedrez(orientacion_blancas=self.juego_con_blancas)
            if self.asistente.engine:
                self.evaluador_simulacion = EvaluadorSimulacion(self.asistente.engine, lock=self.asistente.engine_lock)

            def get_tablero_info():
                coords = None
                if self.asistente and hasattr(self.asistente, "detector"):
                    coords = getattr(self.asistente.detector, "coordenadas", None)
                with self.state_lock:
                    return {
                        "coords": coords,
                        "orientacion_blancas": not self.state["flip"],
                        "board": self.state["board"].copy()
                    }

            self.monitor_raton = MonitorRatonAjedrez(get_tablero_info)
            self.monitor_raton.start()
        except Exception as e:
            with self.state_lock:
                self.state["status"] = f"Error: {e}"
            return

        tablero_anterior = None
        ultimo_resalte = []

        while self.running:
            if self.estado_app != "JUGANDO":
                time.sleep(0.1)
                tablero_anterior = None
                ultimo_resalte = []
                continue

            try:
                time.sleep(0.15)
                flip = self.state["flip"]
                orientacion_actual = not flip

                casillas, img_tablero = self.asistente.detector.obtener_casillas(orientacion_blancas=orientacion_actual)
                
                tr_status = self.asistente.estado_tracker
                with self.state_lock:
                    self.state["tracker_status"] = tr_status

                if casillas is None or img_tablero is None:
                    with self.state_lock:
                        self.state["status"] = "Buscando tablero en pantalla..."
                    continue

                with self.state_lock:
                    if self.state["status"] == "Buscando tablero en pantalla...":
                        self.state["status"] = "En Vivo"

                columnas = ["a", "b", "c", "d", "e", "f", "g", "h"] if orientacion_actual else ["h", "g", "f", "e", "d", "c", "b", "a"]
                filas = ["8", "7", "6", "5", "4", "3", "2", "1"] if orientacion_actual else ["1", "2", "3", "4", "5", "6", "7", "8"]

                piezas_vistas = {}
                nuevo_tablero = chess.Board(None)
                for r_idx, fila in enumerate(filas):
                    for c_idx, col in enumerate(columnas):
                        sq_name = f"{col}{fila}"
                        img_sq = casillas[sq_name]
                        es_clara = (c_idx + r_idx) % 2 == 0
                        pieza = self.asistente.clasificar_casilla(img_sq, es_clara)
                        piezas_vistas[sq_name] = pieza
                        if pieza != "empty":
                            sq_idx = chess.parse_square(sq_name)
                            nuevo_tablero.set_piece_at(sq_idx, chess.Piece.from_symbol(pieza))

                resaltes = self._detectar_resalte_ultima_jugada(img_tablero, orientacion_actual)
                nuevo_tablero, jugada_str = self._resolver_posicion(nuevo_tablero, tablero_anterior, piezas_vistas, resaltes)
                cambio_posicion = nuevo_tablero is not tablero_anterior
                flechas_vis = self._detectar_flechas_visuales(img_tablero, orientacion_actual, nuevo_tablero)

                if not cambio_posicion and resaltes == ultimo_resalte:
                    with self.state_lock:
                        self.state["flechas_visuales"] = flechas_vis
                    continue

                turno_actual = "w" if nuevo_tablero.turn == chess.WHITE else "b"
                es_mi_turno = (turno_actual == self.mi_color_str)
                nombre_turno = "¡TU TURNO!" if es_mi_turno else "Rival pensando..."

                if cambio_posicion:
                    self.ghost_step = 0
                    if self.monitor_raton:
                        self.monitor_raton.reset()

                with self.state_lock:
                    self.state["board"] = nuevo_tablero
                    self.state["flechas_visuales"] = flechas_vis
                    self.state["turno_actual"] = turno_actual
                    self.state["es_mi_turno"] = es_mi_turno
                    self.state["turn_name"] = nombre_turno
                    if cambio_posicion:
                        self.state["simulacion_activa"] = False
                        self.state["simulacion_res"] = None
                        self.state["simulacion_orig_sq"] = None
                        self.state["simulacion_curr_sq"] = None
                    if jugada_str:
                        if not self.state["move_history"] or self.state["move_history"][-1] != jugada_str:
                            self.state["move_history"].append(jugada_str)
                            try:
                                orig_str, dest_str = jugada_str.split(" → ")
                                self.state["last_move"] = chess.Move(chess.parse_square(orig_str.lower()), chess.parse_square(dest_str.lower()))
                            except Exception:
                                pass

                # Detectar fin de partida (Jaque Mate / Ahogado)
                game_over_tipo = None
                game_over_sub = ""
                try:
                    if nuevo_tablero.is_checkmate():
                        yo_gane = (turno_actual != self.mi_color_str)
                        if yo_gane:
                            game_over_tipo = "VICTORIA"
                            game_over_sub = "¡Has ganado la partida por jaque mate!"
                        else:
                            game_over_tipo = "DERROTA"
                            game_over_sub = "El rival ha ganado por jaque mate"
                    elif nuevo_tablero.is_stalemate():
                        game_over_tipo = "TABLAS"
                        game_over_sub = "Partida empatada por rey ahogado"
                except Exception:
                    pass

                # Guardar estados de referencia
                tablero_anterior = nuevo_tablero
                ultimo_resalte = resaltes

                # Si hay fin de partida
                if game_over_tipo:
                    with self.state_lock:
                        self.state["game_over"] = game_over_tipo
                        self.state["game_over_subtitle"] = game_over_sub
                        self.state["best_move"] = None
                        self.state["turn_name"] = "Fin de partida"
                        self.state["mate_in"] = None
                        self.state["pv_moves"] = []
                        self.state["mentor_idea"] = ""
                # Si es mi turno, consultar a Stockfish y mostrar la flecha recomendada
                elif es_mi_turno:
                    res = self.asistente.obtener_mejor_jugada(nuevo_tablero.fen(), tiempo_analisis=0.25)
                    jugada_best = res.move
                    eval_str = res.eval_str
                    pv_moves = res.pv_moves
                    mentor_idea = res.idea
                    mate_in = res.mate_in
                    is_mate_for_white = res.is_mate_for_white

                    score_num = 0.0
                    try:
                        if eval_str.startswith("#"):
                            m_val = int(eval_str.replace("#", "").replace("+", ""))
                            score_num = 15.0 if m_val > 0 else -15.0
                        elif eval_str != "N/A":
                            score_num = float(eval_str.replace("+", ""))
                    except Exception:
                        score_num = 0.0

                    es_mate_usuario = (self.mi_color_str == "w" and is_mate_for_white) or (self.mi_color_str == "b" and is_mate_for_white is False)

                    with self.state_lock:
                        self.state["best_move"] = jugada_best
                        self.state["best_score_obj"] = res.score_obj
                        self.state["eval_str"] = eval_str
                        self.state["eval_score"] = score_num
                        self.state["pv_moves"] = pv_moves
                        self.state["mentor_idea"] = mentor_idea
                        self.state["mate_in"] = mate_in if es_mate_usuario else None
                        self.state["game_over"] = None
                        self.state["game_over_subtitle"] = ""
                else:
                    with self.state_lock:
                        self.state["best_move"] = None
                        self.state["mentor_idea"] = ""
                        self.state["game_over"] = None
                        self.state["game_over_subtitle"] = ""

            except Exception:
                time.sleep(0.3)

    def square_to_screen(self, square, flip=None):
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        
        if flip is None:
            flip = self.state["flip"]
        col = file if not flip else 7 - file
        row = (7 - rank) if not flip else rank

        bx = 50 + self.eval_bar_width
        by = 40
        return bx + col * self.square_size, by + row * self.square_size

    def draw_board(self, tablero_revision=None, flip_revision=False):
        bx = 50 + self.eval_bar_width
        by = 40

        for r in range(8):
            for c in range(8):
                is_light = (r + c) % 2 == 0
                color = COLOR_SQ_LIGHT if is_light else COLOR_SQ_DARK
                rect = pygame.Rect(bx + c * self.square_size, by + r * self.square_size, self.square_size, self.square_size)
                pygame.draw.rect(self.screen, color, rect)

        # Determinar si estamos visualizando una jugada futura en el Tablero Fantasma
        pv_list = self.state.get("pv_moves", [])
        en_fantasma = tablero_revision is None and self.ghost_step > 0 and len(pv_list) >= self.ghost_step

        if tablero_revision is not None:
            tablero_a_dibujar = tablero_revision
        elif en_fantasma:
            # Replicar tablero base y avanzar los movimientos de la variante hasta ghost_step
            tablero_a_dibujar = self.state["board"].copy()
            tablero_a_dibujar.turn = chess.WHITE if self.state["turno_actual"] == "w" else chess.BLACK
            jugadas_previas = pv_list[:self.ghost_step]
            for m in jugadas_previas:
                if m in tablero_a_dibujar.legal_moves:
                    tablero_a_dibujar.push(m)
                else:
                    break

            # Resaltar la última jugada del futuro en azul traslúcido
            mov_actual = jugadas_previas[-1]
            for sq in [mov_actual.from_square, mov_actual.to_square]:
                sx, sy = self.square_to_screen(sq)
                hl_surf = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                hl_surf.fill((100, 180, 255, 130))
                self.screen.blit(hl_surf, (sx, sy))
        else:
            tablero_a_dibujar = self.state["board"]
            last_move = self.state["last_move"]
            if last_move and self.estado_app == "JUGANDO":
                for sq in [last_move.from_square, last_move.to_square]:
                    sx, sy = self.square_to_screen(sq)
                    hl_surf = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                    hl_surf.fill(COLOR_HIGHLIGHT)
                    self.screen.blit(hl_surf, (sx, sy))

        flip = self.state["flip"] if tablero_revision is None else flip_revision
        files = ["a", "b", "c", "d", "e", "f", "g", "h"] if not flip else ["h", "g", "f", "e", "d", "c", "b", "a"]
        ranks = ["8", "7", "6", "5", "4", "3", "2", "1"] if not flip else ["1", "2", "3", "4", "5", "6", "7", "8"]

        for i in range(8):
            lbl = self.font_small.render(files[i], True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl, (bx + i * self.square_size + self.square_size // 2 - 4, by + self.board_size + 6))
            lbl_r = self.font_small.render(ranks[i], True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_r, (bx - 16, by + i * self.square_size + self.square_size // 2 - 6))

        # Dibujar piezas
        for sq in chess.SQUARES:
            piece = tablero_a_dibujar.piece_at(sq)
            if piece:
                color_prefix = "w" if piece.color == chess.WHITE else "b"
                key = f"{color_prefix}{piece.symbol().upper()}"
                img = self.scaled_piece_images.get(key)
                if img:
                    sx, sy = self.square_to_screen(sq, flip)
                    if en_fantasma:
                        p_surf = img.copy()
                        p_surf.set_alpha(225)
                        self.screen.blit(p_surf, (sx, sy))
                    else:
                        self.screen.blit(img, (sx, sy))

        if tablero_revision is not None:
            return

        # Dibujar flechas
        sim_activa = self.state.get("simulacion_activa", False)
        sim_res = self.state.get("simulacion_res")
        sim_orig = self.state.get("simulacion_orig_sq")
        sim_curr = self.state.get("simulacion_curr_sq")

        if en_fantasma:
            mov_actual = pv_list[self.ghost_step - 1]
            es_jugada_mia = (self.ghost_step % 2 == 1)
            f_color = COLOR_ARROW if es_jugada_mia else (240, 150, 50)
            self.draw_arrow(mov_actual.from_square, mov_actual.to_square, color=f_color)

            # Banner superior de Vista Futura
            banner_rect = pygame.Rect(bx, by, self.board_size, 30)
            banner_surf = pygame.Surface((self.board_size, 30), pygame.SRCALPHA)
            banner_surf.fill((20, 24, 34, 215))
            self.screen.blit(banner_surf, (bx, by))
            pygame.draw.line(self.screen, (100, 180, 255), (bx, by + 29), (bx + self.board_size, by + 29), 2)

            txt_fantasma = f"👻 VISTA FUTURA: +{self.ghost_step} jugada(s)  [Rueda / 0 para LIVE]"
            lbl_f = self.font_ghost.render(txt_fantasma, True, (240, 245, 255))
            self.screen.blit(lbl_f, (banner_rect.centerx - lbl_f.get_width() // 2, banner_rect.centery - lbl_f.get_height() // 2))
        elif sim_activa and sim_orig:
            # Resaltar casilla de origen
            sx, sy = self.square_to_screen(chess.parse_square(sim_orig))
            hl_orig = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
            hl_orig.fill((246, 238, 90, 150))
            self.screen.blit(hl_orig, (sx, sy))

            if sim_res and sim_curr:
                color_v = sim_res.color_rgb
                dx, dy = self.square_to_screen(chess.parse_square(sim_curr))
                hl_dest = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                hl_dest.fill((color_v[0], color_v[1], color_v[2], 140))
                self.screen.blit(hl_dest, (dx, dy))

                self.draw_arrow(chess.parse_square(sim_orig), chess.parse_square(sim_curr), color=color_v)

                banner_surf = pygame.Surface((self.board_size, 30), pygame.SRCALPHA)
                banner_surf.fill((20, 24, 34, 225))
                self.screen.blit(banner_surf, (bx, by))
                pygame.draw.line(self.screen, color_v, (bx, by + 29), (bx + self.board_size, by + 29), 2)

                txt_sim = f"🏹 FLECHA: {sim_orig.upper()} → {sim_curr.upper()}   [{sim_res.badge_text}]"
                lbl_sim = self.font_ghost.render(txt_sim, True, color_v)
                self.screen.blit(lbl_sim, (bx + self.board_size // 2 - lbl_sim.get_width() // 2, by + 7))
            elif sim_curr:
                dx, dy = self.square_to_screen(chess.parse_square(sim_curr))
                hl_dest = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                hl_dest.fill((100, 180, 255, 140))
                self.screen.blit(hl_dest, (dx, dy))

                self.draw_arrow(chess.parse_square(sim_orig), chess.parse_square(sim_curr), color=(100, 180, 255))

                banner_surf = pygame.Surface((self.board_size, 30), pygame.SRCALPHA)
                banner_surf.fill((20, 24, 34, 225))
                self.screen.blit(banner_surf, (bx, by))
                pygame.draw.line(self.screen, COLOR_WAITING, (bx, by + 29), (bx + self.board_size, by + 29), 2)

                txt_sim = f"🏹 FLECHA: {sim_orig.upper()} → {sim_curr.upper()}   [Analizando...]"
                lbl_sim = self.font_ghost.render(txt_sim, True, (240, 240, 245))
                self.screen.blit(lbl_sim, (bx + self.board_size // 2 - lbl_sim.get_width() // 2, by + 7))
            else:
                banner_surf = pygame.Surface((self.board_size, 30), pygame.SRCALPHA)
                banner_surf.fill((20, 24, 34, 225))
                self.screen.blit(banner_surf, (bx, by))
                pygame.draw.line(self.screen, COLOR_WAITING, (bx, by + 29), (bx + self.board_size, by + 29), 2)

                txt_sim = f"🏹 DIBUJANDO FLECHA DESDE {sim_orig.upper()}..."
                lbl_sim = self.font_ghost.render(txt_sim, True, (240, 240, 245))
                self.screen.blit(lbl_sim, (bx + self.board_size // 2 - lbl_sim.get_width() // 2, by + 7))
        else:
            best_move = self.state["best_move"]
            if best_move and self.state["es_mi_turno"] and self.estado_app == "JUGANDO":
                self.draw_arrow(best_move.from_square, best_move.to_square)

        # Celebración de Victoria / Fin de partida si corresponde
        if self.state.get("game_over"):
            self.draw_victory_ribbon()

    def draw_arrow(self, from_sq, to_sq, color=None, flip=None):
        x1, y1 = self.square_to_screen(from_sq, flip)
        x2, y2 = self.square_to_screen(to_sq, flip)
        
        start = (x1 + self.square_size // 2, y1 + self.square_size // 2)
        end = (x2 + self.square_size // 2, y2 + self.square_size // 2)

        base_col = color if color else COLOR_ARROW
        pulse = math.sin(time.time() * 5.0) * 45 + 185
        arrow_color = (base_col[0], base_col[1], base_col[2], int(pulse))

        arrow_surf = pygame.Surface((self.win_width, self.win_height), pygame.SRCALPHA)

        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dist = math.hypot(dx, dy)
        if dist < 1:
            return

        angle = math.atan2(dy, dx)
        head_len = max(16, int(self.square_size * 0.35))
        shaft_width = max(6, int(self.square_size * 0.14))

        shorten = int(self.square_size * 0.2)
        real_end = (end[0] - shorten * math.cos(angle), end[1] - shorten * math.sin(angle))

        p_tip = real_end
        p_left = (real_end[0] - head_len * math.cos(angle - math.pi / 6),
                  real_end[1] - head_len * math.sin(angle - math.pi / 6))
        p_right = (real_end[0] - head_len * math.cos(angle + math.pi / 6),
                   real_end[1] - head_len * math.sin(angle + math.pi / 6))

        base_head = (real_end[0] - (head_len * 0.7) * math.cos(angle),
                     real_end[1] - (head_len * 0.7) * math.sin(angle))
        
        pygame.draw.line(arrow_surf, arrow_color, start, base_head, shaft_width)
        pygame.draw.polygon(arrow_surf, arrow_color, [p_tip, p_left, p_right])
        pygame.draw.circle(arrow_surf, arrow_color, start, int(self.square_size * 0.18))

        self.screen.blit(arrow_surf, (0, 0))

    def draw_victory_ribbon(self):
        bx = 50 + self.eval_bar_width
        by = 40
        b_size = self.board_size

        tipo = self.state.get("game_over")
        sub = self.state.get("game_over_subtitle", "")

        # Overlay acrílico translúcido sobre el tablero
        overlay = pygame.Surface((b_size, b_size), pygame.SRCALPHA)
        overlay.fill((15, 18, 24, 160))
        self.screen.blit(overlay, (bx, by))

        # Tarjeta de victoria centrada
        card_w = min(420, b_size - 40)
        card_h = 130
        cx = bx + (b_size - card_w) // 2
        cy = by + (b_size - card_h) // 2

        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((25, 28, 36, 235))
        self.screen.blit(card_surf, (cx, cy))

        borde_color = (235, 185, 55) if tipo == "VICTORIA" else ((220, 80, 80) if tipo == "DERROTA" else (160, 165, 178))
        pygame.draw.rect(self.screen, borde_color, (cx, cy, card_w, card_h), width=2, border_radius=10)

        pygame.draw.line(self.screen, borde_color, (cx + 20, cy + 4), (cx + card_w - 20, cy + 4), 3)

        if tipo == "VICTORIA":
            title_text = "🏆 ¡VICTORIA POR JAQUE MATE!"
        elif tipo == "DERROTA":
            title_text = "⚔️ DERROTA POR JAQUE MATE"
        else:
            title_text = "🤝 TABLAS"

        lbl_tit = self.font_victory.render(title_text, True, borde_color)
        self.screen.blit(lbl_tit, (cx + card_w // 2 - lbl_tit.get_width() // 2, cy + 22))

        lbl_sub = self.font_victory_sub.render(sub, True, COLOR_TEXT_MAIN)
        self.screen.blit(lbl_sub, (cx + card_w // 2 - lbl_sub.get_width() // 2, cy + 60))

        lbl_act = self.font_small.render("Pulsa 'Nueva Partida' en el panel lateral", True, COLOR_TEXT_MUTED)
        self.screen.blit(lbl_act, (cx + card_w // 2 - lbl_act.get_width() // 2, cy + 92))

    def draw_eval_bar(self):
        bx = 18
        by = 40
        h = self.board_size
        w = self.eval_bar_width

        target = self.state["eval_score"]
        self.current_eval_visual += (target - self.current_eval_visual) * 0.1

        clamped = max(-6.0, min(6.0, self.current_eval_visual))
        porc_blancas = 1.0 / (1.0 + math.exp(-0.6 * clamped))

        pygame.draw.rect(self.screen, (40, 40, 42), (bx, by, w, h), border_radius=4)
        
        h_blancas = int(h * porc_blancas)
        y_blancas = by + h - h_blancas
        pygame.draw.rect(self.screen, (245, 245, 248), (bx, y_blancas, w, h_blancas), border_radius=4)
        pygame.draw.rect(self.screen, (70, 75, 85), (bx, by, w, h), width=1, border_radius=4)

        eval_txt = self.state["eval_str"] if self.estado_app == "JUGANDO" else "--"
        txt_surf = self.font_eval.render(eval_txt, True, (20, 20, 20) if porc_blancas > 0.5 else (240, 240, 240))
        pos_y = by + h - 18 if porc_blancas > 0.5 else by + 6
        self.screen.blit(txt_surf, (bx + w // 2 - txt_surf.get_width() // 2, pos_y))

    def draw_panel(self):
        px = self.panel_x
        py = 40
        pw = self.panel_width
        ph = self.board_size

        pygame.draw.rect(self.screen, COLOR_PANEL, (px, py, pw, ph), border_radius=10)

        # Cabecera
        title = self.font_title.render("STOCKFISH LIVE", True, COLOR_TEXT_MAIN)
        self.screen.blit(title, (px + 18, py + 18))
        
        status_txt = self.state["status"]
        status_color = COLOR_ACCENT if status_txt == "En Vivo" else COLOR_WAITING
        lbl_status = self.font_small.render(f"● {status_txt}", True, status_color)
        self.screen.blit(lbl_status, (px + 18, py + 46))

        # Indicador de Tracker
        tracker_state = self.state.get("tracker_status", "BUSCANDO")
        tr_txt = "● Enganchado" if tracker_state == "ENGANCHADO" else "◌ Buscando"
        tr_color = COLOR_ACCENT if tracker_state == "ENGANCHADO" else COLOR_WAITING
        lbl_tr = self.font_small.render(tr_txt, True, tr_color)
        self.screen.blit(lbl_tr, (px + pw - lbl_tr.get_width() - 18, py + 46))

        # RENDERIZADO SEGÚN ESTADO DE LA APP
        if self.estado_app == "SELECCIONANDO":
            # Tarjeta de Selección de Bando
            card_rect = pygame.Rect(px + 16, py + 74, pw - 32, 190)
            pygame.draw.rect(self.screen, COLOR_CARD, card_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_WAITING, card_rect, width=2, border_radius=8)

            lbl_elige = self.font_bold.render("ELIGE TU BANDO", True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl_elige, (card_rect.centerx - lbl_elige.get_width() // 2, card_rect.y + 14))

            lbl_sub = self.font_small.render("¿Con qué piezas vas a jugar?", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_sub, (card_rect.centerx - lbl_sub.get_width() // 2, card_rect.y + 36))

            # Botón Blancas
            hover_b = self.btn_blancas_rect.collidepoint(self.mouse_pos)
            color_btn_b = (250, 250, 255) if hover_b else (235, 235, 240)
            pygame.draw.rect(self.screen, color_btn_b, self.btn_blancas_rect, border_radius=6)
            if hover_b:
                pygame.draw.rect(self.screen, COLOR_ACCENT, self.btn_blancas_rect, width=2, border_radius=6)
            txt_b = self.font_btn.render("♔  JUGAR CON BLANCAS", True, (20, 20, 20))
            self.screen.blit(txt_b, (self.btn_blancas_rect.centerx - txt_b.get_width() // 2,
                                     self.btn_blancas_rect.centery - txt_b.get_height() // 2))

            # Botón Negras
            hover_n = self.btn_negras_rect.collidepoint(self.mouse_pos)
            color_btn_n = (45, 48, 58) if hover_n else (25, 27, 34)
            pygame.draw.rect(self.screen, color_btn_n, self.btn_negras_rect, border_radius=6)
            pygame.draw.rect(self.screen, COLOR_ACCENT if hover_n else (70, 75, 85), self.btn_negras_rect, width=2 if hover_n else 1, border_radius=6)
            txt_n = self.font_btn.render("♚  JUGAR CON NEGRAS", True, (240, 240, 245))
            self.screen.blit(txt_n, (self.btn_negras_rect.centerx - txt_n.get_width() // 2,
                                     self.btn_negras_rect.centery - txt_n.get_height() // 2))

            # Explicación abajo
            info_y = py + 280
            lbl_info1 = self.font_regular.render("El escaneo y el motor se", True, COLOR_TEXT_MUTED)
            lbl_info2 = self.font_regular.render("activarán al hacer tu elección.", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_info1, (px + 20, info_y))
            self.screen.blit(lbl_info2, (px + 20, info_y + 20))

            lbl_help = self.font_small.render("ESC para salir", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_help, (px + pw // 2 - lbl_help.get_width() // 2, py + ph - 24))
            self._dibujar_boton_pgn(self.btn_abrir_pgn_rect, "Abrir PGN")

        else:
            # ESTADO: JUGANDO (Panel Completo en Vivo)
            y_cursor = py + 74
            bando_nombre = "BLANCAS" if self.juego_con_blancas else "NEGRAS"
            badge_bg = (240, 240, 245) if self.juego_con_blancas else (25, 25, 28)
            badge_fg = (20, 20, 20) if self.juego_con_blancas else (235, 235, 240)

            pygame.draw.rect(self.screen, COLOR_CARD, (px + 16, y_cursor, pw - 32, 42), border_radius=6)
            lbl_t = self.font_regular.render("Tu bando:", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_t, (px + 28, y_cursor + 11))
            
            badge_rect = pygame.Rect(px + pw - 110, y_cursor + 8, 85, 26)
            pygame.draw.rect(self.screen, badge_bg, badge_rect, border_radius=13)
            lbl_turn_name = self.font_bold.render(bando_nombre, True, badge_fg)
            self.screen.blit(lbl_turn_name, (badge_rect.centerx - lbl_turn_name.get_width() // 2, 
                                              badge_rect.centery - lbl_turn_name.get_height() // 2))

            # Si la partida ha terminado, mostrar tarjeta de Fin de Partida
            if self.state.get("game_over"):
                y_cursor += 52
                gov_rect = pygame.Rect(px + 16, y_cursor, pw - 32, 136)
                pygame.draw.rect(self.screen, COLOR_CARD, gov_rect, border_radius=8)
                gov_tipo = self.state["game_over"]
                gov_color = (235, 185, 55) if gov_tipo == "VICTORIA" else ((220, 80, 80) if gov_tipo == "DERROTA" else (160, 165, 178))
                pygame.draw.rect(self.screen, gov_color, gov_rect, width=2, border_radius=8)

                lbl_fin = self.font_bold.render(f"PARTIDA TERMINADA", True, gov_color)
                self.screen.blit(lbl_fin, (gov_rect.x + 14, gov_rect.y + 12))

                lbl_det = self.font_small.render(self.state.get("game_over_subtitle", ""), True, COLOR_TEXT_MAIN)
                self.screen.blit(lbl_det, (gov_rect.x + 14, gov_rect.y + 36))

                # Botón Nueva Partida
                self.btn_reset_game_rect = pygame.Rect(gov_rect.x + 14, gov_rect.y + 72, gov_rect.width - 28, 44)
                hover_reset = self.btn_reset_game_rect.collidepoint(self.mouse_pos)
                col_reset = COLOR_ACCENT_HOVER if hover_reset else COLOR_ACCENT
                pygame.draw.rect(self.screen, col_reset, self.btn_reset_game_rect, border_radius=6)
                txt_r = self.font_btn.render("↺  NUEVA PARTIDA", True, (255, 255, 255))
                self.screen.blit(txt_r, (self.btn_reset_game_rect.centerx - txt_r.get_width() // 2,
                                         self.btn_reset_game_rect.centery - txt_r.get_height() // 2))

                y_cursor += 148
            elif self.state.get("simulacion_activa"):
                # ESTADO: SIMULACIÓN EN VIVO (Arrastre en Chess.com)
                y_cursor += 48
                sim_res = self.state.get("simulacion_res")
                sim_orig = self.state.get("simulacion_orig_sq", "")
                sim_curr = self.state.get("simulacion_curr_sq", "")

                card_h = 164 if sim_res else 115
                card_rect = pygame.Rect(px + 16, y_cursor, pw - 32, card_h)
                pygame.draw.rect(self.screen, COLOR_CARD, card_rect, border_radius=8)

                b_color = sim_res.color_rgb if sim_res else COLOR_WAITING
                pygame.draw.rect(self.screen, b_color, card_rect, width=2, border_radius=8)

                if sim_res:
                    # Badge Veredicto
                    lbl_badge = self.font_bold.render(sim_res.badge_text, True, b_color)
                    self.screen.blit(lbl_badge, (card_rect.x + 14, card_rect.y + 10))

                    # Jugada
                    m_txt = f"{sim_orig.upper()}  →  {sim_curr.upper()}"
                    lbl_m = self.font_move.render(m_txt, True, COLOR_TEXT_MAIN)
                    self.screen.blit(lbl_m, (card_rect.x + 14, card_rect.y + 32))

                    # Evaluación y Delta
                    delta_txt = f"Pérdida: -{sim_res.delta:.1f}" if sim_res.delta > 0.05 else "Óptima"
                    eval_info = f"Eval: {sim_res.eval_str}  ({delta_txt})"
                    lbl_ev = self.font_small.render(eval_info, True, COLOR_TEXT_MUTED)
                    self.screen.blit(lbl_ev, (card_rect.x + 14, card_rect.y + 66))

                    # Explicación táctica del Mentor (con ajuste de línea si es largo)
                    expl = sim_res.explanation
                    max_chars = max(24, int((pw - 55) / 7.0))
                    if len(expl) > max_chars:
                        cut_idx = expl[:max_chars].rfind(" ")
                        if cut_idx == -1:
                            cut_idx = max_chars
                        part1 = expl[:cut_idx]
                        part2 = expl[cut_idx:].strip()
                        lbl_exp1 = self.font_idea.render(f"💡 {part1}", True, (230, 235, 245))
                        lbl_exp2 = self.font_idea.render(f"   {part2}", True, (230, 235, 245))
                        self.screen.blit(lbl_exp1, (card_rect.x + 14, card_rect.y + 88))
                        self.screen.blit(lbl_exp2, (card_rect.x + 14, card_rect.y + 108))
                    else:
                        lbl_exp = self.font_idea.render(f"💡 {expl}", True, (230, 235, 245))
                        self.screen.blit(lbl_exp, (card_rect.x + 14, card_rect.y + 88))

                    # Indicador de ayuda
                    lbl_cancel = self.font_small.render("Click izq. o tap derecho para borrar", True, COLOR_TEXT_MUTED)
                    self.screen.blit(lbl_cancel, (card_rect.x + 14, card_rect.y + card_h - 22))
                else:
                    lbl_tit = self.font_bold.render("🏹 FLECHA (CLICK DERECHO)", True, COLOR_WAITING)
                    self.screen.blit(lbl_tit, (card_rect.x + 14, card_rect.y + 12))

                    lbl_s = self.font_regular.render(f"Desde {sim_orig.upper()} hacia...", True, COLOR_TEXT_MAIN)
                    self.screen.blit(lbl_s, (card_rect.x + 14, card_rect.y + 40))

                    lbl_inst = self.font_small.render("Arrastra con click derecho hacia destino", True, COLOR_TEXT_MUTED)
                    self.screen.blit(lbl_inst, (card_rect.x + 14, card_rect.y + 68))

                self.ghost_pill_rects = []
                y_cursor += card_h + 10
            else:
                # Si hay mate in N a favor del usuario, mostrar Pill de Mate destacado
                mate_val = self.state.get("mate_in")
                if mate_val:
                    y_cursor += 48
                    mate_pill_rect = pygame.Rect(px + 16, y_cursor, pw - 32, 28)
                    pulse_m = math.sin(time.time() * 6.0) * 20 + 235
                    col_mate_bg = (int(min(255, pulse_m)), 170, 40)
                    pygame.draw.rect(self.screen, col_mate_bg, mate_pill_rect, border_radius=14)
                    txt_m = f"⚡ MATE EN {mate_val} JUGADA{'S' if mate_val > 1 else ''}"
                    lbl_m = self.font_mate.render(txt_m, True, (20, 20, 20))
                    self.screen.blit(lbl_m, (mate_pill_rect.centerx - lbl_m.get_width() // 2,
                                             mate_pill_rect.centery - lbl_m.get_height() // 2))
                    y_cursor += 34
                else:
                    y_cursor += 48

                # Tarjeta Mejor Jugada / Estado de Turno
                es_mi_turno = self.state["es_mi_turno"]
                idea_txt = self.state.get("mentor_idea", "")
                card_h = 132 if (es_mi_turno and idea_txt) else 102
                card_rect = pygame.Rect(px + 16, y_cursor, pw - 32, card_h)
                pygame.draw.rect(self.screen, COLOR_CARD, card_rect, border_radius=8)
                
                borde_color = COLOR_ACCENT if es_mi_turno else COLOR_WAITING
                pygame.draw.rect(self.screen, borde_color, card_rect, width=2, border_radius=8)

                lbl_sug_texto = "MEJOR JUGADA RECOMENDADA" if es_mi_turno else "TURNO DEL RIVAL"
                lbl_sug = self.font_small.render(lbl_sug_texto, True, borde_color)
                self.screen.blit(lbl_sug, (card_rect.x + 14, card_rect.y + 10))

                best = self.state["best_move"]
                if es_mi_turno and best:
                    orig = str(best)[:2].upper()
                    dest = str(best)[2:4].upper()
                    move_str = f"{orig}  →  {dest}"
                elif es_mi_turno and not best:
                    move_str = "Calculando..."
                else:
                    move_str = "Rival pensando..."

                move_render = self.font_move.render(move_str, True, COLOR_TEXT_MAIN)
                self.screen.blit(move_render, (card_rect.x + 14, card_rect.y + 32))

                # Modo Mentor: Idea táctica o estratégica debajo de la jugada
                if es_mi_turno and idea_txt:
                    lbl_idea = self.font_idea.render(f"💡 {idea_txt}", True, (215, 235, 175))
                    self.screen.blit(lbl_idea, (card_rect.x + 14, card_rect.y + 68))
                    ev_y = card_rect.y + 98
                else:
                    ev_y = card_rect.y + 68

                ev_sub = self.font_regular.render(f"Ventaja: {self.state['eval_str']}", True, COLOR_TEXT_MUTED)
                self.screen.blit(ev_sub, (card_rect.x + 14, ev_y))

                y_cursor += card_h + 10

                # Micro-Pills del Tablero Fantasma (Futuro)
                pv_list = self.state.get("pv_moves", [])
                self.ghost_pill_rects = []
                if pv_list and es_mi_turno:
                    lbl_scroller = self.font_small.render("Tablero Fantasma (Línea Futura):", True, COLOR_TEXT_MUTED)
                    self.screen.blit(lbl_scroller, (px + 18, y_cursor))
                    y_cursor += 18

                    pill_w = 42
                    pill_h = 24
                    total_pills = min(5, len(pv_list) + 1)
                    for p_idx in range(total_pills):
                        pill_x = px + 18 + p_idx * (pill_w + 6)
                        p_rect = pygame.Rect(pill_x, y_cursor, pill_w, pill_h)
                        self.ghost_pill_rects.append((p_idx, p_rect))

                        is_active = (self.ghost_step == p_idx)
                        is_hover = p_rect.collidepoint(self.mouse_pos)
                        
                        if is_active:
                            bg_col = (100, 180, 255)
                            fg_col = (15, 20, 30)
                        elif is_hover:
                            bg_col = (65, 75, 95)
                            fg_col = COLOR_TEXT_MAIN
                        else:
                            bg_col = COLOR_CARD
                            fg_col = COLOR_TEXT_MUTED

                        pygame.draw.rect(self.screen, bg_col, p_rect, border_radius=4)
                        p_label = "LIVE" if p_idx == 0 else f"+{p_idx}"
                        lbl_p = self.font_ghost.render(p_label, True, fg_col)
                        self.screen.blit(lbl_p, (p_rect.centerx - lbl_p.get_width() // 2,
                                                 p_rect.centery - lbl_p.get_height() // 2))

                    y_cursor += 32

            # Historial de Movimientos Detectados
            lbl_hist = self.font_bold.render("Movimientos Detectados", True, COLOR_TEXT_MAIN)
            self.screen.blit(lbl_hist, (px + 18, y_cursor))

            h_restante = max(60, ph - (y_cursor - py) - 50)
            hist_box = pygame.Rect(px + 16, y_cursor + 24, pw - 32, h_restante)
            pygame.draw.rect(self.screen, COLOR_CARD, hist_box, border_radius=6)

            history = self.state["move_history"]
            line_y = hist_box.y + 10
            max_lines = max(1, (h_restante - 16) // 22)
            for idx, m_txt in enumerate(history[-max_lines:]):
                lbl_m = self.font_regular.render(f"• {m_txt}", True, COLOR_TEXT_MAIN)
                self.screen.blit(lbl_m, (hist_box.x + 14, line_y))
                line_y += 22

            # Botón cambiar bando / ayuda abajo
            hover_cambiar = self.btn_cambiar_rect.collidepoint(self.mouse_pos)
            pygame.draw.rect(self.screen, COLOR_BTN_HOVER if hover_cambiar else COLOR_CARD, self.btn_cambiar_rect, border_radius=4)
            pygame.draw.rect(self.screen, COLOR_ACCENT if hover_cambiar else (70, 75, 85), self.btn_cambiar_rect, width=1, border_radius=4)
            lbl_btn_c = self.font_small.render("⇄ Cambiar Bando", True, COLOR_TEXT_MAIN if hover_cambiar else COLOR_TEXT_MUTED)
            self.screen.blit(lbl_btn_c, (self.btn_cambiar_rect.centerx - lbl_btn_c.get_width() // 2,
                                         self.btn_cambiar_rect.centery - lbl_btn_c.get_height() // 2))

            lbl_help = self.font_small.render("[F] Bando | [R] Reiniciar | ESC", True, COLOR_TEXT_MUTED)
            self.screen.blit(lbl_help, (px + 18, py + ph - 24))

    def _abrir_dialogo_pgn(self):
        import tkinter as tk
        from tkinter import filedialog, messagebox

        ventana = tk.Tk()
        try:
            ventana.withdraw()
            ventana.attributes('-topmost', True)
            ruta = filedialog.askopenfilename(
                parent=ventana, title='Abrir partida PGN', filetypes=[('Partidas PGN', '*.pgn')],
            )
            if ruta:
                try:
                    self._mostrar_partida_pgn(cargar_partida(ruta), os.path.basename(ruta))
                except (OSError, ValueError) as error:
                    messagebox.showerror('No se pudo abrir el PGN', str(error), parent=ventana)
        finally:
            ventana.destroy()

    def _mostrar_partida_pgn(self, partida, archivo):
        self._cancelar_revision_pgn()
        self.pgn_partida = partida
        self.pgn_archivo = archivo
        self.pgn_bando = None
        self.pgn_sesion = None
        self.pgn_estado = ''
        self.pgn_origen = None
        self.pgn_controles = []
        self.estado_app = 'REVISION_PGN'

    def _cancelar_revision_pgn(self):
        if self.pgn_trabajo is not None:
            cancelar, _ = self.pgn_trabajo
            cancelar.set()
            self.pgn_trabajo = None

    def _analizar_pgn(self, bando):
        partida = self.pgn_partida
        self.pgn_bando = bando

        def analizar(motor, cancelar, mensajes):
            errores = revisar_partida(
                partida, bando, motor, cancelado=cancelar.is_set,
                progreso=lambda hechos, total: mensajes.put(('progreso', f'Analizando {hechos} de {total} jugadas…')),
            )
            if errores:
                mensajes.put(('progreso', 'Buscando buenas alternativas…'))
            preparados = []
            for error in errores:
                if cancelar.is_set():
                    return []
                preparados.append(preparar_alternativas(error, motor))
            return preparados

        self._iniciar_trabajo_pgn(analizar, 'resultado', 'Iniciando Stockfish…')

    def _analizar_intento_pgn(self, error, jugada):
        def analizar(motor, _cancelar, _mensajes):
            return evaluar_alternativa(error, jugada, motor)

        self._iniciar_trabajo_pgn(analizar, 'intento', 'Evaluando tu jugada…')

    def _iniciar_trabajo_pgn(self, analizar, tipo_resultado, estado):
        cancelar = threading.Event()
        mensajes = SimpleQueue()
        self.pgn_trabajo = cancelar, mensajes
        self.pgn_estado = estado

        def ejecutar():
            try:
                if cancelar.is_set():
                    return
                with chess.engine.SimpleEngine.popen_uci(obtener_ruta_stockfish(), timeout=5) as motor:
                    resultado = analizar(motor, cancelar, mensajes)
                mensajes.put((tipo_resultado, resultado))
            except Exception as error:
                mensajes.put(('fallo', str(error)))

        threading.Thread(target=ejecutar, name='revision-pgn').start()

    def _actualizar_revision_pgn(self):
        if self.pgn_trabajo is None:
            return
        _, mensajes = self.pgn_trabajo
        while True:
            try:
                tipo, dato = mensajes.get_nowait()
            except Empty:
                return
            if tipo == 'progreso':
                self.pgn_estado = dato
            else:
                self.pgn_trabajo = None
                if tipo == 'fallo':
                    self.pgn_estado = f'No se pudo completar el análisis. {dato}'
                elif tipo == 'intento':
                    if dato:
                        self.pgn_sesion.aceptar_alternativa(dato)
                        self.pgn_estado = '¡Buena alternativa!'
                    else:
                        self.pgn_estado = 'Jugada legal. Probá una opción más fuerte.'
                elif dato:
                    self.pgn_sesion = SesionRevision(dato)
                    self.pgn_estado = ''
                else:
                    self.pgn_estado = 'Sin caídas de al menos medio peón para este bando.'
                return

    def _casilla_pgn(self, pos):
        x, y = pos
        col = (x - 50 - self.eval_bar_width) // self.square_size
        fila = (y - 40) // self.square_size
        if 0 <= col < 8 and 0 <= fila < 8:
            return chess.square(7 - col, fila) if self.pgn_bando == chess.BLACK else chess.square(col, 7 - fila)
        return None

    def _dibujar_boton_pgn(self, rect, etiqueta, seleccionado=False):
        fondo = COLOR_ACCENT if seleccionado else COLOR_BTN_HOVER if rect.collidepoint(self.mouse_pos) else COLOR_CARD
        pygame.draw.rect(self.screen, fondo, rect, border_radius=6)
        texto = self.font_regular.render(etiqueta, True, COLOR_TEXT_MAIN)
        self.screen.blit(texto, texto.get_rect(center=rect.center))

    def _dibujar_revision_pgn(self):
        self._actualizar_revision_pgn()
        sesion = self.pgn_sesion
        flip = self.pgn_bando == chess.BLACK
        color_intento = (100, 180, 255)
        tablero = sesion.tablero if sesion else self.pgn_partida.board()
        self.draw_board(tablero, flip)
        if sesion and sesion.solucion_visible:
            variante = sesion.variante
            if sesion.paso == 0 and not sesion.en_practica:
                jugada = sesion.error.jugada
                self.draw_arrow(jugada.from_square, jugada.to_square, COLOR_WAITING, flip=flip)
            jugada = variante[max(0, sesion.paso - 1)]
            self.draw_arrow(jugada.from_square, jugada.to_square, flip=flip)
        elif self.pgn_origen is not None:
            destino = self._casilla_pgn(self.mouse_pos)
            if destino is not None:
                self.draw_arrow(self.pgn_origen, destino, color_intento, flip=flip)

        x, y = self.panel_x, 40
        ancho, alto = self.panel_width, max(370, self.board_size)
        pygame.draw.rect(self.screen, COLOR_PANEL, (x, y, ancho, alto), border_radius=10)
        self.pgn_controles = []

        def texto(contenido, dy, fuente=None, color=COLOR_TEXT_MAIN, lineas=1):
            fuente = fuente or self.font_regular
            margen = ancho - 32
            renglones = textwrap.wrap(contenido, width=max(15, margen // 7)) if lineas > 1 else [contenido]
            for indice, renglon in enumerate(renglones[:lineas]):
                superficie = fuente.render(renglon, True, color)
                self.screen.blit(superficie, (x + 16, y + dy + 18 * indice), (0, 0, margen, superficie.get_height()))

        def boton(accion, etiqueta, dy, dx=16, ancho_boton=None, seleccionado=False):
            rect = pygame.Rect(x + dx, y + dy, ancho_boton or ancho - 32, 28)
            self.pgn_controles.append((accion, rect))
            self._dibujar_boton_pgn(rect, etiqueta, seleccionado)

        texto('REVISIÓN PGN', 15, self.font_title)
        texto(self.pgn_archivo, 45, self.font_small, COLOR_TEXT_MUTED)
        mitad = (ancho - 40) // 2
        boton('abrir', 'Abrir otro', alto - 36, 16, mitad)
        boton('volver', 'Volver', alto - 36, 24 + mitad, mitad)

        if sesion is None:
            if self.pgn_trabajo is not None:
                texto(self.pgn_estado, 78, color=COLOR_WAITING)
            else:
                texto('¿Qué bando querés revisar?', 78)
                boton('blancas', 'Blancas', 108, 16, mitad)
                boton('negras', 'Negras', 108, 24 + mitad, mitad)
                texto(self.pgn_estado, 151, color=COLOR_TEXT_MUTED, lineas=4)
            return

        texto('Errores · de mayor a menor gravedad', 63, self.font_small, COLOR_TEXT_MUTED)
        ancho_indice = (ancho - 48) // 3
        for indice, _ in enumerate(sesion.errores):
            boton(indice, str(indice + 1), 82, 16 + (ancho_indice + 8) * indice, ancho_indice, indice == sesion.indice)

        error = sesion.error
        if sesion.en_practica and not sesion.solucion_visible:
            texto('Encontrá la jugada', 119, self.font_bold)
            texto('Mantené el clic derecho sobre la pieza.', 148, lineas=2)
            texto('Arrastrá hasta la casilla destino y soltá.', 190, lineas=2)
            texto('Azul · La flecha que dibujás', 232, self.font_small, color_intento)
            texto(self.pgn_estado, 253, color=COLOR_WAITING, lineas=3)
            boton('revelar', 'Ver solución', 302)
            return

        inicial = error.tablero
        jugada_linea = sesion.variante[0]
        puntos = '...' if inicial.turn == chess.BLACK else '.'
        perdida = 'Cambio de mate' if error.cambio_mate else f'−{error.perdida / 100:.2f} peones'
        texto(f'{inicial.fullmove_number}{puntos} {inicial.san(error.jugada)}  ·  {perdida}', 119, self.font_bold)
        if not sesion.en_practica:
            texto('Naranja · Tu jugada (paso 0)', 142, self.font_small, COLOR_WAITING)
        texto('Verde · Variante de Stockfish', 157, self.font_small, COLOR_ARROW)
        estado_paso = 'Antes del error' if sesion.paso == 0 else 'Variante recomendada'
        texto(f'Paso {sesion.paso}/{len(sesion.variante)} · {estado_paso}', 175, self.font_small, COLOR_TEXT_MUTED)
        es_alternativa = jugada_linea != error.variante[0]
        etiqueta = 'Tu alternativa' if es_alternativa else 'Stockfish propone'
        texto(f'{etiqueta} {inicial.san(jugada_linea)}', 194)
        detalle = self.pgn_estado or explicar_jugada(inicial.copy(stack=False), jugada_linea)
        texto(detalle, 215, self.font_idea, COLOR_ARROW if es_alternativa else COLOR_TEXT_MUTED, lineas=2)
        boton('anterior', '‹ Anterior', 250, 16, mitad)
        boton('siguiente', 'Siguiente ›', 250, 24 + mitad, mitad)
        texto('← / → o rueda · una jugada por paso', 282, self.font_small, COLOR_TEXT_MUTED)
        boton('practicar', 'Practicar de nuevo' if sesion.en_practica else 'Practicar', 302)

    def _evento_pgn(self, event):
        sesion = self.pgn_sesion
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for accion, rect in self.pgn_controles:
                if not rect.collidepoint(event.pos):
                    continue
                if accion == 'abrir':
                    self._abrir_dialogo_pgn()
                elif accion == 'volver':
                    self._cancelar_revision_pgn()
                    self.volver_a_seleccion()
                elif accion in ('blancas', 'negras') and self.pgn_trabajo is None:
                    self._analizar_pgn(accion == 'blancas')
                elif isinstance(accion, int):
                    self._cancelar_revision_pgn()
                    sesion.seleccionar(accion)
                    self.pgn_estado = ''
                    self.pgn_origen = None
                elif accion == 'practicar':
                    sesion.practicar()
                    self.pgn_estado = ''
                    self.pgn_origen = None
                elif accion == 'revelar':
                    self._cancelar_revision_pgn()
                    sesion.revelar()
                    self.pgn_estado = ''
                    self.pgn_origen = None
                else:
                    sesion.avanzar(1 if accion == 'siguiente' else -1)
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._cancelar_revision_pgn()
            self.volver_a_seleccion()
        elif sesion is not None:
            if event.type == pygame.MOUSEWHEEL:
                sesion.avanzar(event.y)
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                sesion.avanzar(1 if event.key == pygame.K_RIGHT else -1)
            elif not sesion.solucion_visible and self.pgn_trabajo is None:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    self.pgn_origen = self._casilla_pgn(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                    origen, self.pgn_origen = self.pgn_origen, None
                    destino = self._casilla_pgn(event.pos)
                    if origen is not None and destino is not None and origen != destino:
                        mensajes = {
                            'correcta': '¡Encontraste la jugada de Stockfish!',
                            'buena_alternativa': '¡Buena alternativa!',
                            'ilegal': 'Esa jugada no es legal en esta posición.',
                        }
                        intento = sesion.intentar(origen, destino)
                        if intento == 'alternativa':
                            jugada = sesion.error.tablero.find_move(origen, destino)
                            self._analizar_intento_pgn(sesion.error, jugada)
                        else:
                            self.pgn_estado = mensajes[intento]

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_o and event.mod & pygame.KMOD_CTRL:
                    self._abrir_dialogo_pgn()
                elif self.estado_app == 'REVISION_PGN' and event.type != pygame.VIDEORESIZE:
                    self._evento_pgn(event)
                elif event.type == pygame.MOUSEWHEEL:
                    bx = 50 + self.eval_bar_width
                    by = 40
                    board_rect = pygame.Rect(bx, by, self.board_size, self.board_size)
                    if board_rect.collidepoint(self.mouse_pos) and self.estado_app == "JUGANDO":
                        max_steps = len(self.state.get("pv_moves", []))
                        if event.y > 0:
                            if max_steps > 0:
                                self.ghost_step = min(max_steps, self.ghost_step + 1)
                        elif event.y < 0:
                            self.ghost_step = max(0, self.ghost_step - 1)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.estado_app == "SELECCIONANDO":
                            if self.btn_blancas_rect.collidepoint(event.pos):
                                self.seleccionar_bando(True)
                            elif self.btn_negras_rect.collidepoint(event.pos):
                                self.seleccionar_bando(False)
                            elif self.btn_abrir_pgn_rect.collidepoint(event.pos):
                                self._abrir_dialogo_pgn()
                        elif self.estado_app == "JUGANDO":
                            if self.btn_cambiar_rect.collidepoint(event.pos):
                                self.volver_a_seleccion()
                            elif self.state.get("game_over") and self.btn_reset_game_rect.collidepoint(event.pos):
                                self.nueva_partida()
                            else:
                                for p_idx, p_rect in self.ghost_pill_rects:
                                    if p_rect.collidepoint(event.pos):
                                        self.ghost_step = p_idx
                                        break
                elif event.type == pygame.VIDEORESIZE:
                    self.win_width = max(600, event.w)
                    self.win_height = max(420, event.h)
                    self.screen = pygame.display.set_mode((self.win_width, self.win_height), pygame.RESIZABLE)
                    self._recalcular_dimensiones()
                    self.scaled_piece_images = self._scale_piece_images()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_f:
                        if self.estado_app == "JUGANDO":
                            self.volver_a_seleccion()
                    elif event.key == pygame.K_r:
                        if self.estado_app == "JUGANDO":
                            self.nueva_partida()
                    elif event.key == pygame.K_RIGHT:
                        max_steps = len(self.state.get("pv_moves", []))
                        if max_steps > 0:
                            self.ghost_step = min(max_steps, self.ghost_step + 1)
                    elif event.key == pygame.K_LEFT:
                        self.ghost_step = max(0, self.ghost_step - 1)
                    elif event.key in (pygame.K_0, pygame.K_KP0, pygame.K_BACKSPACE):
                        self.ghost_step = 0

            self.screen.fill(COLOR_BG)
            if self.estado_app == 'REVISION_PGN':
                self._dibujar_revision_pgn()
            else:
                self.draw_eval_bar()
                self.draw_board()
                self.draw_panel()
            self._actualizar_cursor_raton()

            pygame.display.flip()
            self.clock.tick(60)

        self._cancelar_revision_pgn()
        if self.monitor_raton:
            self.monitor_raton.stop()
        if self.asistente:
            self.asistente.cerrar()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    print("=" * 60)
    print("        CHESS VISION ASSISTANT (EN VIVO)")
    print("=" * 60)
    print("Abriendo ventana gráfica... Elige tu bando en el panel lateral.")
    app = VisualChessApp()
    app.run()
