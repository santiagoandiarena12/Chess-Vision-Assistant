import io
import os
import unittest
from unittest.mock import patch

import chess
import chess.pgn
import pygame

from interfaz_visual import VisualChessApp
from revision_pgn import ErrorRevision, SesionRevision


class InterfazRevisionPGNTest(unittest.TestCase):
    def test_practica_por_flecha_con_tablero_invertido(self):
        with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'}):
            with patch.object(VisualChessApp, '_background_vision_loop'), patch.object(VisualChessApp, '_simulacion_worker_loop'):
                app = VisualChessApp()
            self.addCleanup(pygame.quit)

        partida = chess.pgn.read_game(io.StringIO('1. e4 e5 *'))
        tablero = partida.board()
        tablero.push_uci('e2e4')
        principal = chess.Move.from_uci('e7e5')
        alternativa = tuple(map(chess.Move.from_uci, ('c7c5', 'g1f3')))
        app._mostrar_partida_pgn(partida, 'prueba.pgn')
        app.pgn_bando = chess.BLACK
        app.pgn_sesion = SesionRevision([
            ErrorRevision(tablero, chess.Move.from_uci('a7a6'), (principal,), 90, alternativas=(alternativa,)),
        ])
        app._dibujar_revision_pgn()

        practica = next(rect for accion, rect in app.pgn_controles if accion == 'practicar')
        app._evento_pgn(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=practica.center))
        self.assertFalse(app.pgn_sesion.solucion_visible)
        # Con negras abajo, c7 queda en columna 5 y fila 6.
        x = 50 + app.eval_bar_width + 5 * app.square_size + app.square_size // 2
        y = 40 + 6 * app.square_size + app.square_size // 2
        app._evento_pgn(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(x, y)))
        app._evento_pgn(pygame.event.Event(pygame.MOUSEBUTTONUP, button=3, pos=(x, y - 2 * app.square_size)))
        self.assertTrue(app.pgn_sesion.solucion_visible)
        self.assertIn('Buena alternativa', app.pgn_estado)
        with patch.object(app, 'draw_arrow') as dibujar_flecha:
            app._dibujar_revision_pgn()
            self.assertEqual(dibujar_flecha.call_args.args[:2], (chess.C7, chess.C5))
        siguiente = dict(app.pgn_controles)['siguiente']
        app._evento_pgn(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=siguiente.center))
        self.assertEqual(app.pgn_sesion.tablero.peek().uci(), 'c7c5')
