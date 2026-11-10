import time
import threading
import ctypes
import chess

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MonitorRatonAjedrez:
    """
    Monitor ligero en segundo plano que detecta el trazo de flechas con click derecho
    en Chess.com (VK_RBUTTON) para evaluar inmediatamente la jugada candidata.
    """
    def __init__(self, obtener_tablero_info_cb):
        self.obtener_tablero_info = obtener_tablero_info_cb
        self.running = False
        self.thread = None
        self.lock = threading.Lock()

        # Estado del trazo con click derecho
        self.r_is_down = False
        self.r_start_sq = None
        self.r_start_pos = (0, 0)
        self.r_has_moved = False

        # Flecha activa detectada
        self.arrow_active = False
        self.arrow_orig_sq = None
        self.arrow_dest_sq = None
        self.arrow_candidate_move = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False

    def reset(self):
        with self.lock:
            self.r_is_down = False
            self.r_start_sq = None
            self.r_has_moved = False
            self.arrow_active = False
            self.arrow_orig_sq = None
            self.arrow_dest_sq = None
            self.arrow_candidate_move = None

    def _pos_a_casilla(self, x, y, coords, orientacion_blancas):
        if not coords:
            return None
        left = coords.get("left", 0)
        top = coords.get("top", 0)
        w = coords.get("width", 0)
        h = coords.get("height", 0)

        if w <= 0 or h <= 0:
            return None
        if x < left or x >= left + w or y < top or y >= top + h:
            return None

        c = int((x - left) * 8 / w)
        r = int((y - top) * 8 / h)
        if c < 0 or c > 7 or r < 0 or r > 7:
            return None

        cols = ["a", "b", "c", "d", "e", "f", "g", "h"] if orientacion_blancas else ["h", "g", "f", "e", "d", "c", "b", "a"]
        fils = ["8", "7", "6", "5", "4", "3", "2", "1"] if orientacion_blancas else ["1", "2", "3", "4", "5", "6", "7", "8"]

        return f"{cols[c]}{fils[r]}"

    def _loop(self):
        pt = POINT()
        while self.running:
            try:
                time.sleep(0.02)  # 50 Hz

                info = self.obtener_tablero_info()
                if not info:
                    self.reset()
                    continue

                coords = info.get("coords")
                orientacion_blancas = info.get("orientacion_blancas", True)
                board = info.get("board")

                if not coords or not board:
                    self.reset()
                    continue

                # Consultar posición del cursor y estado de botones
                ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                rbtn_down = bool(ctypes.windll.user32.GetAsyncKeyState(0x02) & 0x8000)
                lbtn_down = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)

                with self.lock:
                    # 1. Click izquierdo: en Chess.com borra todas las flechas dibujadas
                    if lbtn_down:
                        self.arrow_active = False
                        self.arrow_orig_sq = None
                        self.arrow_dest_sq = None
                        self.arrow_candidate_move = None
                        self.r_is_down = False
                        self.r_start_sq = None
                        self.r_has_moved = False
                        continue

                    # 2. Click derecho: trazo de flecha
                    if rbtn_down:
                        if not self.r_is_down:
                            # Inicio del click derecho
                            self.r_is_down = True
                            self.r_start_pos = (pt.x, pt.y)
                            self.r_has_moved = False
                            sq = self._pos_a_casilla(pt.x, pt.y, coords, orientacion_blancas)
                            self.r_start_sq = sq
                            self.arrow_active = False
                            self.arrow_orig_sq = None
                            self.arrow_dest_sq = None
                            self.arrow_candidate_move = None
                        else:
                            # Arrastre con click derecho
                            dx = abs(pt.x - self.r_start_pos[0])
                            dy = abs(pt.y - self.r_start_pos[1])
                            if dx > 10 or dy > 10:
                                self.r_has_moved = True

                            sq_curr = self._pos_a_casilla(pt.x, pt.y, coords, orientacion_blancas)
                            if self.r_start_sq and sq_curr and sq_curr != self.r_start_sq and self.r_has_moved:
                                orig_idx = chess.parse_square(self.r_start_sq)
                                dest_idx = chess.parse_square(sq_curr)
                                p = board.piece_at(orig_idx)

                                # Verificar coronación si es peón
                                promo = None
                                if p and p.piece_type == chess.PAWN:
                                    dest_rank = chess.square_rank(dest_idx)
                                    if (p.color == chess.WHITE and dest_rank == 7) or (p.color == chess.BLACK and dest_rank == 0):
                                        promo = chess.QUEEN

                                m = chess.Move(orig_idx, dest_idx, promotion=promo)
                                self.arrow_active = True
                                self.arrow_orig_sq = self.r_start_sq
                                self.arrow_dest_sq = sq_curr
                                self.arrow_candidate_move = m
                    else:
                        if self.r_is_down:
                            # Se soltó el botón derecho
                            self.r_is_down = False
                            if not self.r_has_moved:
                                # Fue solo un clic rápido sobre una casilla sin arrastrar -> Chess.com borra flechas
                                self.arrow_active = False
                                self.arrow_orig_sq = None
                                self.arrow_dest_sq = None
                                self.arrow_candidate_move = None
                                self.r_start_sq = None
                            else:
                                # Se completó el trazo de la flecha: confirmar posición final del cursor
                                sq_final = self._pos_a_casilla(pt.x, pt.y, coords, orientacion_blancas)
                                if self.r_start_sq and sq_final and sq_final != self.r_start_sq:
                                    orig_idx = chess.parse_square(self.r_start_sq)
                                    dest_idx = chess.parse_square(sq_final)
                                    p = board.piece_at(orig_idx)
                                    promo = None
                                    if p and p.piece_type == chess.PAWN:
                                        dest_rank = chess.square_rank(dest_idx)
                                        if (p.color == chess.WHITE and dest_rank == 7) or (p.color == chess.BLACK and dest_rank == 0):
                                            promo = chess.QUEEN
                                    m = chess.Move(orig_idx, dest_idx, promotion=promo)
                                    self.arrow_active = True
                                    self.arrow_dest_sq = sq_final
                                    self.arrow_candidate_move = m

            except Exception:
                time.sleep(0.05)

    def obtener_estado(self):
        with self.lock:
            return {
                "active": self.arrow_active,
                "orig_sq": self.arrow_orig_sq,
                "dest_sq": self.arrow_dest_sq,
                "candidate_move": self.arrow_candidate_move,
                "is_drawing": self.r_is_down,
                "drawing_orig": self.r_start_sq
            }
