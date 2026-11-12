import threading
import time
import unittest
from unittest.mock import Mock
import cv2
import numpy as np
import chess
import py_compile

from chess_vision.interfaz.interfaz_visual import VisualChessApp
from chess_vision.asistente import AsistenteAjedrez
from chess_vision import rutas


class VisionYMotorTest(unittest.TestCase):
    def setUp(self):
        self.app = VisualChessApp.__new__(VisualChessApp)

    def test_deteccion_flecha_caballo_en_l_con_corte_morfologico(self):
        # Tablero sintético 400x400 (50x50 por casilla)
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        # Flecha en L de G1 (325, 375) -> G3 (325, 275) -> H3 (375, 275)
        # Color naranja Chess.com BGR: (30, 180, 240)
        cv2.line(img, (325, 375), (325, 275), (30, 180, 240), 14)
        cv2.arrowedLine(img, (325, 275), (375, 275), (30, 180, 240), 14, tipLength=0.4)
        # Simular corte oscuro entre g1 y g2 provocado por el borde de la pieza
        img[345:350, :] = 0

        tablero = chess.Board()
        flechas = self.app._detectar_flechas_visuales(img, True, tablero)
        self.assertEqual(len(flechas), 1)
        orig, dest, mov = flechas[0]
        self.assertEqual((orig, dest), ("g1", "h3"))
        self.assertEqual(mov.uci(), "g1h3")

    def test_deteccion_flecha_recta_peon(self):
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        # Flecha de avance E2 (225, 325) -> E4 (225, 225)
        cv2.arrowedLine(img, (225, 325), (225, 225), (30, 180, 240), 12, tipLength=0.3)
        tablero = chess.Board()
        flechas = self.app._detectar_flechas_visuales(img, True, tablero)
        self.assertEqual(len(flechas), 1)
        orig, dest, mov = flechas[0]
        self.assertEqual((orig, dest), ("e2", "e4"))

    def test_deteccion_tablero_sin_flechas_retorna_vacio(self):
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        flechas = self.app._detectar_flechas_visuales(img, True, chess.Board())
        self.assertEqual(flechas, [])

    def test_seguridad_concurrente_engine_lock(self):
        motor_mock = Mock()
        asistente = AsistenteAjedrez.__new__(AsistenteAjedrez)
        asistente.engine = motor_mock
        asistente.engine_lock = threading.Lock()

        # Simular acceso simultáneo desde dos hilos protegidos por el lock
        resultados = []
        def tarea_hilo(id_hilo):
            with asistente.engine_lock:
                time.sleep(0.01)
                resultados.append(id_hilo)

        h1 = threading.Thread(target=tarea_hilo, args=(1,))
        h2 = threading.Thread(target=tarea_hilo, args=(2,))
        h1.start()
        h2.start()
        h1.join()
        h2.join()

        self.assertEqual(sorted(resultados), [1, 2])

    def test_asegurar_motor_reconecta_tras_fallo(self):
        asistente = AsistenteAjedrez.__new__(AsistenteAjedrez)
        asistente.engine_lock = threading.Lock()
        motor_caido = Mock()
        motor_caido.ping.side_effect = RuntimeError("Proceso de Stockfish cerrado")
        asistente.engine = motor_caido

        nuevo_motor = Mock()
        asistente._iniciar_motor = Mock(side_effect=lambda: setattr(asistente, "engine", nuevo_motor))

        motor_listo = asistente.asegurar_motor()
        self.assertEqual(motor_listo, nuevo_motor)
        asistente._iniciar_motor.assert_called_once()

    def test_compilacion_y_sintaxis_de_modulos(self):
        # Validar compilación estática de archivos clave sin errores de sintaxis
        raiz = rutas.RAIZ_PROYECTO / "chess_vision"
        archivos = [
            raiz / "asistente.py",
            raiz / "analisis" / "evaluador_simulacion.py",
            raiz / "analisis" / "revision_pgn.py",
            raiz / "interfaz" / "interfaz_visual.py",
        ]
        for ruta in archivos:
            res = py_compile.compile(str(ruta), doraise=True)
            self.assertTrue(res is not None)


if __name__ == "__main__":
    unittest.main()
