import json
import time
from pathlib import Path

import cv2
import mss
import numpy as np

from chess_vision.captura.detector_tablero import DetectorTablero
from chess_vision.rutas import COORDENADAS, ruta_local

class TableroDetector:
    def __init__(self, config_path=COORDENADAS):
        self.config_path = Path(config_path)
        self.detector_auto = DetectorTablero()
        self.estado_tracker = "BUSCANDO"
        self.ultimo_escaneo = 0.0
        self.coordenadas = self._cargar_coordenadas()
        self.sct = mss.mss()

    def _cargar_coordenadas(self):
        config = ruta_local(COORDENADAS) if self.config_path == COORDENADAS else self.config_path
        if config.is_file():
            try:
                with config.open(encoding="utf-8") as f:
                    data = json.load(f)
                    if all(k in data for k in ("top", "left", "width", "height")):
                        return data
            except Exception:
                pass
        return None

    def _guardar_coordenadas(self, coords):
        self.coordenadas = coords
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(coords, f, indent=4)
        except Exception:
            pass

    def capturar_tablero(self):
        """
        Captura el área del tablero.
        Si la región actual es válida, la devuelve en ~2ms (modo ENGANCHADO).
        Si la ventana se movió o descalibró, re-escanea la pantalla (modo BUSCANDO).
        """
        # 1. Si tenemos coordenadas previas, probar captura directa
        if self.coordenadas is not None:
            try:
                bbox = {
                    "top": int(self.coordenadas["top"]),
                    "left": int(self.coordenadas["left"]),
                    "width": int(self.coordenadas["width"]),
                    "height": int(self.coordenadas["height"])
                }
                screenshot = self.sct.grab(bbox)
                img = np.array(screenshot)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

                if self.detector_auto.verificar_es_tablero(img_bgr):
                    self.estado_tracker = "ENGANCHADO"
                    return img_bgr
                else:
                    self.estado_tracker = "BUSCANDO"
            except Exception:
                self.estado_tracker = "BUSCANDO"

        # 2. Si no es válido o no hay coordenadas, re-escanear pantalla completa (con throttle de 1.0s)
        ahora = time.time()
        if ahora - self.ultimo_escaneo < 1.0:
            return None

        self.ultimo_escaneo = ahora
        nuevas_coords = self.detector_auto.buscar_en_pantalla(self.sct, self.sct.monitors)

        if nuevas_coords is not None and nuevas_coords["top"] >= 0 and nuevas_coords["left"] >= 0:
            self._guardar_coordenadas(nuevas_coords)
            self.estado_tracker = "ENGANCHADO"
            try:
                screenshot = self.sct.grab(nuevas_coords)
                img = np.array(screenshot)
                return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            except Exception:
                return None
        else:
            self.estado_tracker = "BUSCANDO"
            return None

    def obtener_casillas(self, orientacion_blancas=True):
        """
        Divide el tablero capturado en un diccionario con las 64 casillas.
        orientacion_blancas: True si juegas con blancas, False con negras.
        Retorna: (dict {'e4': img, ...}, tablero_img) o (None, None) si no se detectó tablero.
        """
        tablero_img = self.capturar_tablero()
        if tablero_img is None:
            return None, None

        h, w, _ = tablero_img.shape
        sq_w = w / 8.0
        sq_h = h / 8.0

        columnas = ["a", "b", "c", "d", "e", "f", "g", "h"] if orientacion_blancas else ["h", "g", "f", "e", "d", "c", "b", "a"]
        filas = ["8", "7", "6", "5", "4", "3", "2", "1"] if orientacion_blancas else ["1", "2", "3", "4", "5", "6", "7", "8"]

        casillas = {}
        for r in range(8):
            for c in range(8):
                y1 = int(r * sq_h)
                y2 = int((r + 1) * sq_h)
                x1 = int(c * sq_w)
                x2 = int((c + 1) * sq_w)
                
                nombre_casilla = f"{columnas[c]}{filas[r]}"
                casillas[nombre_casilla] = tablero_img[y1:y2, x1:x2]

        return casillas, tablero_img
