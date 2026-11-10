import os
import json
import time
import cv2
import numpy as np
from tablero import TableroDetector

CARPETA_PIEZAS = "piezas"

def sintetizar_pieza(pieza_src, fondo_src, fondo_dst, salida):
    src = cv2.imread(os.path.join(CARPETA_PIEZAS, pieza_src))
    f_src = cv2.imread(os.path.join(CARPETA_PIEZAS, fondo_src))
    f_dst = cv2.imread(os.path.join(CARPETA_PIEZAS, fondo_dst))
    if src is None or f_src is None or f_dst is None:
        return

    h, w = src.shape[:2]
    f_src = cv2.resize(f_src, (w, h))
    f_dst = cv2.resize(f_dst, (w, h))

    diff = cv2.cvtColor(cv2.absdiff(src, f_src), cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
    mask_blur = cv2.GaussianBlur(mask, (3, 3), 0) / 255.0
    mask_3d = mask_blur[:, :, None]

    comp = (src.astype(float) * mask_3d + f_dst.astype(float) * (1.0 - mask_3d)).astype(np.uint8)
    cv2.imwrite(os.path.join(CARPETA_PIEZAS, salida), comp)

def capturar_y_guardar_piezas(orientacion_blancas=True):
    os.makedirs(CARPETA_PIEZAS, exist_ok=True)
    detector = TableroDetector()
    
    print("=" * 65)
    print("       EXTRACTOR AUTOMÁTICO DE PIEZAS (v4)")
    print("=" * 65)
    print("Asegúrate de que el tablero esté en POSICIÓN INICIAL y visible.")
    print("-" * 65)
    
    for i in range(4, 0, -1):
        print(f"   Capturando en {i}...", flush=True)
        time.sleep(1)

    casillas, tablero_img = detector.obtener_casillas(orientacion_blancas=orientacion_blancas)
    print("\n¡Captura realizada!")

    mapa_inicial = {
        # Fila 8 (Negras)
        "a8": ("negra", "r", "clara"),
        "h8": ("negra", "r", "oscura"),
        "b8": ("negra", "n", "oscura"),
        "g8": ("negra", "n", "clara"),
        "c8": ("negra", "b", "clara"),
        "f8": ("negra", "b", "oscura"),
        "d8": ("negra", "q", "oscura"),
        "e8": ("negra", "k", "clara"),
        
        # Fila 7 (Peones negros)
        "a7": ("negra", "p", "oscura"),
        "b7": ("negra", "p", "clara"),
        
        # Casillas vacías centrales
        "d4": ("vacia", "empty", "oscura"),
        "e4": ("vacia", "empty", "clara"),
        
        # Fila 2 (Peones blancos)
        "a2": ("blanca", "P", "clara"),
        "b2": ("blanca", "P", "oscura"),
        
        # Fila 1 (Blancas)
        "a1": ("blanca", "R", "oscura"),
        "h1": ("blanca", "R", "clara"),
        "b1": ("blanca", "N", "clara"),
        "g1": ("blanca", "N", "oscura"),
        "c1": ("blanca", "B", "oscura"),
        "f1": ("blanca", "B", "clara"),
        "d1": ("blanca", "Q", "clara"),
        "e1": ("blanca", "K", "oscura"),
    }

    # Limpiar carpeta previa
    for arch in os.listdir(CARPETA_PIEZAS):
        try:
            os.remove(os.path.join(CARPETA_PIEZAS, arch))
        except Exception:
            pass

    guardadas = 0
    for casilla, (bando, pieza, tipo_casilla) in mapa_inicial.items():
        if casilla in casillas:
            img_casilla = casillas[casilla]
            nombre_archivo = f"{bando}_pieza_{pieza}_{tipo_casilla}.png"
            ruta = os.path.join(CARPETA_PIEZAS, nombre_archivo)
            cv2.imwrite(ruta, img_casilla)
            guardadas += 1

    # Sintetizar las versiones faltantes de reyes y reinas en casilla opuesta
    print("Generando variantes para casillas claras y oscuras de Reyes y Reinas...")
    sintetizar_pieza("blanca_pieza_K_oscura.png", "vacia_pieza_empty_oscura.png", "vacia_pieza_empty_clara.png", "blanca_pieza_K_clara.png")
    sintetizar_pieza("negra_pieza_k_clara.png", "vacia_pieza_empty_clara.png", "vacia_pieza_empty_oscura.png", "negra_pieza_k_oscura.png")
    sintetizar_pieza("blanca_pieza_Q_clara.png", "vacia_pieza_empty_clara.png", "vacia_pieza_empty_oscura.png", "blanca_pieza_Q_oscura.png")
    sintetizar_pieza("negra_pieza_q_oscura.png", "vacia_pieza_empty_oscura.png", "vacia_pieza_empty_clara.png", "negra_pieza_q_clara.png")

    cv2.imwrite("captura_piezas_verificacion.png", tablero_img)
    total = len(os.listdir(CARPETA_PIEZAS))
    print(f"\n[OK] ¡Total de plantillas completas listas: {total}!")

if __name__ == "__main__":
    capturar_y_guardar_piezas()
