import chess
import chess.engine
from mentor_ajedrez import explicar_jugada

PIEZA_NOMBRES = {
    chess.PAWN: "el peón",
    chess.KNIGHT: "el caballo",
    chess.BISHOP: "el alfil",
    chess.ROOK: "la torre",
    chess.QUEEN: "la dama",
    chess.KING: "el rey"
}

class SimulacionResultado:
    def __init__(self, move, verdict, badge_text, delta, eval_str, explanation, color_rgb, opp_reply=None):
        self.move = move
        self.verdict = verdict
        self.badge_text = badge_text
        self.delta = delta
        self.eval_str = eval_str
        self.explanation = explanation
        self.color_rgb = color_rgb
        self.opp_reply = opp_reply

    def __repr__(self):
        return f"<SimulacionResultado {self.move} {self.verdict} delta={self.delta:.2f} eval={self.eval_str}>"


class EvaluadorSimulacion:
    def __init__(self, engine=None, lock=None):
        self.engine = engine
        self.lock = lock
        self._cache = {}

    def evaluar_candidata(self, board, move, best_move=None, best_score_obj=None, eval_optima_str="0.0", tiempo_analisis=0.15):
        """
        Evalúa una jugada candidata que el usuario está simulando (flecha en Chess.com)
        y la compara rigurosamente con la mejor jugada de la posición.
        """
        if not board or not move:
            return None

        # Si es coronación de peón y no tiene promoción explícita, asumir Dama
        piece = board.piece_at(move.from_square)
        if piece and piece.piece_type == chess.PAWN:
            to_rank = chess.square_rank(move.to_square)
            if (piece.color == chess.WHITE and to_rank == 7) or (piece.color == chess.BLACK and to_rank == 0):
                if not move.promotion:
                    move = chess.Move(move.from_square, move.to_square, promotion=chess.QUEEN)

        # Validación de jugada legal
        if move not in board.legal_moves:
            try:
                piece = board.piece_at(move.from_square)
                color_jugador = piece.color if piece else board.turn
                if piece and color_jugador != board.turn:
                    msg = "No es el turno de esa pieza."
                elif piece and board.is_pinned(color_jugador, move.from_square):
                    msg = "Movimiento no permitido: la pieza está clavada al rey."
                else:
                    msg = "Movimiento no permitido por las reglas del ajedrez."
            except Exception:
                msg = "Movimiento no permitido en esta posición."

            return SimulacionResultado(
                move=move,
                verdict="NO_LEGAL",
                badge_text="⚠️ NO ES JUGADA LEGAL",
                delta=0.0,
                eval_str="--",
                explanation=msg,
                color_rgb=(180, 180, 190)
            )

        cache_key = (board.fen(), move.uci())
        if cache_key in self._cache:
            return self._cache[cache_key]

        # CASO 1: Si coincide exactamente con la mejor jugada recomendada por Stockfish
        if best_move and move == best_move:
            idea = explicar_jugada(board, move)
            if not idea:
                idea = "¡Es la mejor jugada recomendada por el motor!"
            res = SimulacionResultado(
                move=move,
                verdict="EXCELENTE",
                badge_text="🟢 ¡MEJOR JUGADA!",
                delta=0.0,
                eval_str=eval_optima_str,
                explanation=idea,
                color_rgb=(46, 204, 113)
            )
            self._cache[cache_key] = res
            return res

        b_next = board.copy()
        b_next.push(move)

        # CASO 2: Jaque Mate directo dado por el usuario
        if b_next.is_checkmate():
            res = SimulacionResultado(
                move=move,
                verdict="EXCELENTE",
                badge_text="🟢 ¡JAQUE MATE!",
                delta=0.0,
                eval_str="#+1",
                explanation="¡Jaque mate directo! Ganas la partida de inmediato.",
                color_rgb=(46, 204, 113)
            )
            self._cache[cache_key] = res
            return res

        if not self.engine:
            res = SimulacionResultado(
                move=move,
                verdict="BUENA",
                badge_text="JUGADA LEGAL",
                delta=0.0,
                eval_str="--",
                explanation=explicar_jugada(board, move),
                color_rgb=(78, 172, 80)
            )
            self._cache[cache_key] = res
            return res

        # CASO 3: Análisis con Stockfish protegido por Lock
        info = None
        try:
            if self.lock:
                with self.lock:
                    info = self.engine.analyse(b_next, chess.engine.Limit(time=tiempo_analisis))
            else:
                info = self.engine.analyse(b_next, chess.engine.Limit(time=tiempo_analisis))
        except Exception:
            # Fallback seguro para no trabar la interfaz
            res = SimulacionResultado(
                move=move,
                verdict="BUENA",
                badge_text="🔵 MOVIMIENTO ANALIZADO",
                delta=0.0,
                eval_str=eval_optima_str,
                explanation=explicar_jugada(board, move) or "Movimiento táctico en análisis...",
                color_rgb=(52, 152, 219)
            )
            return res

        score = info.get("score") if info else None
        pv = info.get("pv", []) if info else []
        opp_move = pv[0] if pv else None

        if not score:
            res = SimulacionResultado(
                move=move,
                verdict="BUENA",
                badge_text="🔵 MOVIMIENTO ANALIZADO",
                delta=0.0,
                eval_str=eval_optima_str,
                explanation=explicar_jugada(board, move) or "Movimiento analizado.",
                color_rgb=(52, 152, 219)
            )
            return res

        # Evaluación desde el POV del jugador que realizó el movimiento
        player_turn = board.turn
        score_cand_pov = score.pov(player_turn)
        is_mate_for_me = score_cand_pov.is_mate()
        mate_val = score_cand_pov.mate() if is_mate_for_me else None

        if is_mate_for_me:
            cand_num = 50.0 if (mate_val and mate_val > 0) else -50.0
            eval_cand_str = f"#{mate_val:+d}" if mate_val else "#"
        else:
            cand_num = (score_cand_pov.score() or 0) / 100.0
            eval_cand_str = f"{cand_num:+.2f}"

        # Obtener valor numérico de la evaluación óptima desde el mismo POV
        if best_score_obj:
            best_pov = best_score_obj.pov(player_turn)
            if best_pov.is_mate():
                bm = best_pov.mate()
                best_num = 50.0 if (bm and bm > 0) else -50.0
            else:
                best_num = (best_pov.score() or 0) / 100.0
        else:
            try:
                if eval_optima_str.startswith("#"):
                    m_val = int(eval_optima_str.replace("#", "").replace("+", ""))
                    best_num = 50.0 if m_val > 0 else -50.0
                elif eval_optima_str not in ("N/A", "--", ""):
                    val = float(eval_optima_str.replace("+", ""))
                    best_num = val if player_turn == chess.WHITE else -val
                else:
                    best_num = cand_num
            except Exception:
                best_num = cand_num

        delta = max(0.0, best_num - cand_num)

        # 4. Clasificación según la pérdida de centipeones (Delta)
        if is_mate_for_me and mate_val and mate_val < 0:
            verdict = "COLGADA"
            badge_text = "🔴 ¡PERMITE MATE!"
            color_rgb = (235, 60, 60)
        elif delta <= 0.25:
            verdict = "EXCELENTE"
            badge_text = "🟢 ¡EXCELENTE!"
            color_rgb = (46, 204, 113)
        elif delta <= 0.65:
            verdict = "BUENA"
            badge_text = "🟢 BUENA JUGADA"
            color_rgb = (78, 172, 80)
        elif delta <= 1.50:
            verdict = "IMPRECISION"
            badge_text = "🟡 IMPRECISIÓN"
            color_rgb = (235, 195, 50)
        elif delta <= 2.80:
            verdict = "ERROR"
            badge_text = "🟠 ERROR"
            color_rgb = (235, 130, 40)
        else:
            verdict = "COLGADA"
            badge_text = "🔴 ¡GRAVE ERROR / COLGADA!"
            color_rgb = (235, 60, 60)

        # 5. Explicación táctica del Mentor
        if verdict in ("EXCELENTE", "BUENA"):
            idea = explicar_jugada(board, move)
            if not idea:
                idea = "Mantiene la ventaja y la iniciativa en la posición."
            explanation = idea
        else:
            # Describir por qué es mala buscando la refutación del rival
            if opp_move:
                orig_name = chess.square_name(opp_move.from_square).upper()
                dest_name = chess.square_name(opp_move.to_square).upper()
                mov_rival_str = f"{orig_name}→{dest_name}"

                if b_next.is_capture(opp_move):
                    pieza_comida = b_next.piece_at(opp_move.to_square)
                    nombre_comida = PIEZA_NOMBRES.get(pieza_comida.piece_type if pieza_comida else chess.PAWN, "pieza")
                    explanation = f"Te dejas {nombre_comida} en {dest_name} (el rival responderá {mov_rival_str})."
                elif b_next.gives_check(opp_move):
                    explanation = f"Permite jaque peligroso del rival con {mov_rival_str}."
                elif is_mate_for_me and mate_val and mate_val < 0:
                    explanation = f"Permite que el rival inicie una red de mate forzado."
                else:
                    explanation = f"Pierdes ventaja (-{delta:.1f}). El rival responderá {mov_rival_str}."
            else:
                explanation = f"Pierdes la ventaja de la posición (-{delta:.1f})."

        res = SimulacionResultado(
            move=move,
            verdict=verdict,
            badge_text=badge_text,
            delta=delta,
            eval_str=eval_cand_str,
            explanation=explanation,
            color_rgb=color_rgb,
            opp_reply=opp_move
        )

        self._cache[cache_key] = res
        return res
