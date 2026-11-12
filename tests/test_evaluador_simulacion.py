import unittest
from unittest.mock import Mock
import chess
import chess.engine

from chess_vision.analisis.evaluador_simulacion import EvaluadorSimulacion


class EvaluadorSimulacionTest(unittest.TestCase):
    def setUp(self):
        self.motor = Mock(spec=chess.engine.SimpleEngine)
        self.evaluador = EvaluadorSimulacion(self.motor)

    def test_mejor_jugada_coincidente_retorna_delta_cero(self):
        tablero = chess.Board()
        mejor_m = chess.Move.from_uci("e2e4")
        res = self.evaluador.evaluar_candidata(
            tablero, mejor_m, best_move=mejor_m, eval_optima_str="+0.32"
        )
        self.assertEqual(res.verdict, "EXCELENTE")
        self.assertEqual(res.badge_text, "🟢 ¡MEJOR JUGADA!")
        self.assertEqual(res.delta, 0.0)

    def test_jugada_dudosa_blancas_calcula_delta_positivo(self):
        tablero = chess.Board()
        mejor_m = chess.Move.from_uci("e2e4")
        dudosa = chess.Move.from_uci("f2f3")
        score_optimo = chess.engine.PovScore(chess.engine.Cp(32), chess.WHITE)
        # En b_next (tras f2f3) le toca a Negras y están mejor (+68 para Negras, -68 para Blancas)
        score_cand = chess.engine.PovScore(chess.engine.Cp(68), chess.BLACK)

        self.motor.analyse.return_value = {
            "score": score_cand,
            "pv": [chess.Move.from_uci("e7e5")],
        }

        res = self.evaluador.evaluar_candidata(
            tablero, dudosa, best_move=mejor_m, best_score_obj=score_optimo
        )
        self.assertIn(res.verdict, ("IMPRECISION", "ERROR"))
        self.assertAlmostEqual(res.delta, 1.0, places=2)

    def test_mejor_jugada_negras_normaliza_pov_correctamente(self):
        tablero = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        mejor_negra = chess.Move.from_uci("c7c5")
        res = self.evaluador.evaluar_candidata(
            tablero, mejor_negra, best_move=mejor_negra, eval_optima_str="-0.30"
        )
        self.assertEqual(res.verdict, "EXCELENTE")
        self.assertEqual(res.badge_text, "🟢 ¡MEJOR JUGADA!")
        self.assertEqual(res.delta, 0.0)

    def test_jugada_erronea_negras_detecta_perdida(self):
        tablero = chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1")
        mejor_negra = chess.Move.from_uci("c7c5")
        erronea = chess.Move.from_uci("f7f6")
        score_optimo = chess.engine.PovScore(chess.engine.Cp(-30), chess.BLACK)
        score_cand = chess.engine.PovScore(chess.engine.Cp(146), chess.WHITE)

        self.motor.analyse.return_value = {
            "score": score_cand,
            "pv": [chess.Move.from_uci("d2d4")],
        }

        res = self.evaluador.evaluar_candidata(
            tablero, erronea, best_move=mejor_negra, best_score_obj=score_optimo
        )
        self.assertIn(res.verdict, ("IMPRECISION", "ERROR"))
        self.assertAlmostEqual(res.delta, 1.16, places=2)

    def test_colgada_grave_asigna_veredicto_colgada_y_refutacion(self):
        tablero = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
        mejor_m = chess.Move.from_uci("f1b5")
        colgada = chess.Move.from_uci("f3e5")
        score_optimo = chess.engine.PovScore(chess.engine.Cp(45), chess.WHITE)
        score_cand = chess.engine.PovScore(chess.engine.Cp(386), chess.BLACK)

        self.motor.analyse.return_value = {
            "score": score_cand,
            "pv": [chess.Move.from_uci("c6e5")],
        }

        res = self.evaluador.evaluar_candidata(
            tablero, colgada, best_move=mejor_m, best_score_obj=score_optimo
        )
        self.assertEqual(res.verdict, "COLGADA")
        self.assertGreater(res.delta, 4.0)
        self.assertIn("Te dejas el caballo", res.explanation)

    def test_movimiento_no_legal_o_fuera_de_turno(self):
        tablero = chess.Board()
        mov_ilegal = chess.Move.from_uci("e1e5")
        res = self.evaluador.evaluar_candidata(tablero, mov_ilegal)
        self.assertEqual(res.verdict, "NO_LEGAL")
        self.assertEqual(res.badge_text, "⚠️ NO ES JUGADA LEGAL")

    def test_jaque_mate_directo_usuario_retorna_mate(self):
        tablero = chess.Board("7k/5Q2/6K1/8/8/8/8/8 w - - 0 1")
        mate_mov = chess.Move.from_uci("f7g7")
        res = self.evaluador.evaluar_candidata(tablero, mate_mov)
        self.assertEqual(res.verdict, "EXCELENTE")
        self.assertEqual(res.badge_text, "🟢 ¡JAQUE MATE!")
        self.assertEqual(res.delta, 0.0)


if __name__ == "__main__":
    unittest.main()
