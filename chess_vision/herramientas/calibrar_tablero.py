import json
import time
import cv2
import mss
import numpy as np
from chess_vision.rutas import COORDENADAS, DATOS_LOCALES

def calibrar():
    print("=" * 60)
    print("      CALIBRADOR DE TABLERO (PANTALLA PRINCIPAL)")
    print("=" * 60)
    print("1. Ten tu juego de ajedrez visible en tu pantalla principal.")
    print("2. En 3 segundos se tomará la captura...")
    
    for i in range(3, 0, -1):
        print(f"   {i}...", flush=True)
        time.sleep(1)

    print("\n¡Captura realizada!")
    with mss.mss() as sct:
        # Monitor 1 es siempre la pantalla principal
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    print("\nINSTRUCCIONES:")
    print(" - Arrastra un recuadro con el ratón sobre el tablero de ajedrez.")
    print(" - Presiona ENTER o BARRA ESPACIADORA para confirmar.")
    print(" - Presiona 'C' para cancelar.")

    window_name = "Selecciona el tablero (ENTER para confirmar)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    roi = cv2.selectROI(window_name, img, fromCenter=False, showCrosshair=True)
    cv2.destroyAllWindows()

    x, y, w, h = roi
    if w == 0 or h == 0:
        print("\n[!] Selección cancelada.")
        return

    coordenadas = {
        "top": int(monitor["top"] + y),
        "left": int(monitor["left"] + x),
        "width": int(w),
        "height": int(h)
    }

    DATOS_LOCALES.mkdir(parents=True, exist_ok=True)
    with COORDENADAS.open("w", encoding="utf-8") as f:
        json.dump(coordenadas, f, indent=4)

    print(f"\n[OK] ¡Coordenadas guardadas en {COORDENADAS}!")
    print(f"     X: {coordenadas['left']}, Y: {coordenadas['top']}, Ancho: {w}, Alto: {h}")

    # Verificación
    tablero = img[y:y+h, x:x+w].copy()
    sq_w = w / 8.0
    sq_h = h / 8.0
    for r in range(8):
        for c in range(8):
            cv2.rectangle(tablero, (int(c*sq_w), int(r*sq_h)), (int((c+1)*sq_w), int((r+1)*sq_h)), (0, 255, 0), 1)

    verificacion = DATOS_LOCALES / "calibracion_resultado.png"
    cv2.imwrite(str(verificacion), tablero)
    print(f"[OK] Verificación guardada en '{verificacion}'.")

if __name__ == "__main__":
    calibrar()
