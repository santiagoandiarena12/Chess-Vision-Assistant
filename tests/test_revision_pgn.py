import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import chess
import chess.engine
import chess.pgn

from chess_vision.analisis import revision_pgn


PGN = '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 1-0'


class RevisionPGNTest(unittest.TestCase):
    def test_multipv_acepta_lineas_cercanas_para_negras(self):
        tablero = chess.Board()
        tablero.push_uci('e2e4')
        mejor, cercana, peor, respuesta = map(chess.Move.from_uci, ('e7e5', 'c7c5', 'a7a6', 'g1f3'))
        error = revision_pgn.ErrorRevision(tablero, peor, (mejor,), 90)

        motor = Mock(spec=chess.engine.SimpleEngine)
        motor.analyse.return_value = [
            {'pv': [mejor], 'score': chess.engine.PovScore(chess.engine.Cp(10), chess.WHITE)},
            {'pv': [cercana, respuesta], 'score': chess.engine.PovScore(chess.engine.Cp(35), chess.WHITE)},
            {'pv': [peor], 'score': chess.engine.PovScore(chess.engine.Cp(36), chess.WHITE)},
        ]

        preparado = revision_pgn.preparar_alternativas(error, motor)
        self.assertEqual(motor.analyse.call_args.kwargs['multipv'], 5)
        self.assertEqual(preparado.alternativas, ((cercana, respuesta),))
        sesion = revision_pgn.SesionRevision([preparado])
        sesion.practicar()
        self.assertEqual(sesion.intentar(chess.A7, chess.A6), 'alternativa')
        self.assertFalse(sesion.solucion_visible)
        self.assertEqual(sesion.intentar(chess.C7, chess.C5), 'buena_alternativa')
        self.assertTrue(sesion.solucion_visible)
        sesion.avanzar(2)
        self.assertEqual([jugada.uci() for jugada in sesion.tablero.move_stack], ['c7c5', 'g1f3'])
        sesion.practicar()
        sesion.revelar()
        self.assertEqual(sesion.variante, (mejor,))

    def test_intento_fuera_de_la_lista_puede_aceptarse(self):
        tablero = chess.Board()
        mejor, intento, respuesta = map(chess.Move.from_uci, ('e2e4', 'd2d4', 'd7d5'))
        error = revision_pgn.ErrorRevision(tablero, chess.Move.from_uci('a2a3'), (mejor,), 100)
        motor = Mock(spec=chess.engine.SimpleEngine)
        motor.analyse.return_value = [
            {'pv': [mejor], 'score': chess.engine.PovScore(chess.engine.Cp(44), chess.WHITE)},
            {'pv': [intento, respuesta], 'score': chess.engine.PovScore(chess.engine.Cp(20), chess.WHITE)},
        ]
        self.assertEqual(revision_pgn.evaluar_alternativa(error, intento, motor), (intento, respuesta))
        self.assertEqual(motor.analyse.call_args.kwargs['root_moves'], [mejor, intento])

    def test_alternativa_no_cuenta_si_pierde_un_mate_forzado(self):
        tablero = chess.Board('7k/5Q2/6K1/8/8/8/8/8 w - - 0 1')
        mejor, pierde_mate = map(chess.Move.from_uci, ('f7g7', 'f7f6'))
        error = revision_pgn.ErrorRevision(tablero, pierde_mate, (mejor,), 300)
        motor = Mock(spec=chess.engine.SimpleEngine)
        motor.analyse.return_value = [
            {'pv': [mejor], 'score': chess.engine.PovScore(chess.engine.Mate(1), chess.WHITE)},
            {'pv': [pierde_mate], 'score': chess.engine.PovScore(chess.engine.Cp(900), chess.WHITE)},
        ]
        self.assertEqual(revision_pgn.preparar_alternativas(error, motor).alternativas, ())

    def test_carga_primera_partida_y_rechaza_archivo_vacio(self):
        with tempfile.NamedTemporaryFile(dir=Path(__file__).parent, suffix='.pgn', delete=False) as archivo:
            ruta = Path(archivo.name)
        try:
            ruta.write_text(f'{PGN}\n\n1. d4 d5 *', encoding='utf-8-sig')
            partida = revision_pgn.cargar_partida(ruta)
            self.assertEqual(next(iter(partida.mainline_moves())).uci(), 'e2e4')
            ruta.write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                revision_pgn.cargar_partida(ruta)
        finally:
            ruta.unlink()

    def test_devuelve_tres_caidas_del_bando_elegido(self):
        partida = chess.pgn.read_game(io.StringIO(PGN))
        mejores = {1: 'c7c5', 2: 'g8f6', 3: 'g8f6', 4: 'd7d6', 5: 'b7b5'}
        perdidas = {1: 70, 2: 5, 3: 220, 4: 110, 5: 90}

        def analyse(tablero, limite, *, root_moves=None):
            self.assertEqual(tablero.turn, chess.BLACK)
            numero = tablero.fullmove_number
            jugada = root_moves[0] if root_moves else chess.Move.from_uci(mejores[numero])
            perdida = perdidas[numero] if root_moves else 0
            return {'pv': [jugada], 'score': chess.engine.PovScore(chess.engine.Cp(-perdida), chess.BLACK)}

        motor = Mock(spec=chess.engine.SimpleEngine)
        motor.analyse.side_effect = analyse
        progreso = []
        errores = revision_pgn.revisar_partida(partida, chess.BLACK, motor, progreso=lambda hechos, total: progreso.append((hechos, total)))

        self.assertEqual([error.jugada.uci() for error in errores], ['a7a6', 'g8f6', 'f8e7'])
        self.assertEqual([error.perdida for error in errores], [220, 110, 90])
        self.assertEqual(progreso[-1], (5, 5))
        self.assertEqual(errores[0].tablero.turn, chess.BLACK)

    def test_revelar_y_practicar_reutiliza_la_posicion_original(self):
        tablero = chess.Board()
        error = revision_pgn.ErrorRevision(
            tablero, chess.Move.from_uci('a2a3'),
            (chess.Move.from_uci('e2e4'), chess.Move.from_uci('e7e5')), 100,
        )
        sesion = revision_pgn.SesionRevision([error])
        sesion.avanzar(2)
        self.assertEqual(sesion.tablero.peek().uci(), 'e7e5')
        sesion.practicar()
        sesion.avanzar(2)
        self.assertEqual(sesion.tablero.fen(), chess.STARTING_FEN)
        self.assertEqual(sesion.intentar(chess.E2, chess.E5), 'ilegal')
        self.assertEqual(sesion.intentar(chess.D2, chess.D4), 'alternativa')
        self.assertFalse(sesion.solucion_visible)
        self.assertEqual(sesion.intentar(chess.E2, chess.E4), 'correcta')
        self.assertTrue(sesion.solucion_visible)
        self.assertEqual(sesion.tablero.fen(), chess.STARTING_FEN)


if __name__ == '__main__':
    unittest.main()
