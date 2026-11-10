import cv2
import numpy as np

class DetectorTablero:
    def __init__(self, min_size=240, max_size=1200):
        self.min_size = min_size
        self.max_size = max_size

    def calcular_score_damero(self, roi_bgr):
        """
        Evalúa si una imagen corresponde a un tablero de ajedrez de 8x8.
        Retorna (score, contraste):
          - score: proporción de casillas que alternan correctamente y diferencia de brillo (0.0 a 1.0)
          - es_valido: True si supera los umbrales de damero
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return 0.0, False

        h, w = roi_bgr.shape[:2]
        if w < self.min_size or h < self.min_size or w > self.max_size or h > self.max_size:
            return 0.0, False

        ratio = w / float(h)
        if ratio < 0.92 or ratio > 1.08:
            return 0.0, False

        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY) if len(roi_bgr.shape) == 3 else roi_bgr

        sq_w = w / 8.0
        sq_h = h / 8.0

        # Muestrear el centro de cada una de las 64 casillas
        grid = np.zeros((8, 8), dtype=np.float32)
        margin_x = max(2, int(sq_w * 0.25))
        margin_y = max(2, int(sq_h * 0.25))

        for r in range(8):
            y1 = int(r * sq_h) + margin_y
            y2 = int((r + 1) * sq_h) - margin_y
            if y2 <= y1:
                y2 = y1 + 1
            for c in range(8):
                x1 = int(c * sq_w) + margin_x
                x2 = int((c + 1) * sq_w) - margin_x
                if x2 <= x1:
                    x2 = x1 + 1
                cell = gray[y1:y2, x1:x2]
                grid[r, c] = float(np.median(cell))

        # Separar casillas claras y oscuras según paridad
        claras = []
        oscuras = []
        for r in range(8):
            for c in range(8):
                if (r + c) % 2 == 0:
                    claras.append(grid[r, c])
                else:
                    oscuras.append(grid[r, c])

        mean_c = np.mean(claras)
        mean_o = np.mean(oscuras)
        diff_contraste = abs(mean_c - mean_o)

        # En cualquier tablero real, la diferencia entre claras y oscuras suele ser > 14
        if diff_contraste < 12.0:
            return 0.0, False

        # Verificar alternancia de signos horizontal y vertical
        transiciones_validas = 0
        total_transiciones = 0

        # Si mean_c > mean_o, paridad 0 es más clara que paridad 1
        espera_par_mayor = (mean_c > mean_o)

        for r in range(8):
            for c in range(7):
                total_transiciones += 1
                diff = grid[r, c] - grid[r, c + 1]
                # Si (r+c)%2 == 0:
                if (r + c) % 2 == 0:
                    if (diff > 2.0 and espera_par_mayor) or (diff < -2.0 and not espera_par_mayor):
                        transiciones_validas += 1
                else:
                    if (diff < -2.0 and espera_par_mayor) or (diff > 2.0 and not espera_par_mayor):
                        transiciones_validas += 1

        for c in range(8):
            for r in range(7):
                total_transiciones += 1
                diff = grid[r, c] - grid[r + 1, c]
                if (r + c) % 2 == 0:
                    if (diff > 2.0 and espera_par_mayor) or (diff < -2.0 and not espera_par_mayor):
                        transiciones_validas += 1
                else:
                    if (diff < -2.0 and espera_par_mayor) or (diff > 2.0 and not espera_par_mayor):
                        transiciones_validas += 1

        ratio_alternancia = transiciones_validas / float(total_transiciones)
        
        # Con piezas, al menos el 58% de las transiciones alternan correctamente
        # En fondos lisos, interfaces de ventanas o ruido, suele dar < 40%
        es_valido = bool(ratio_alternancia >= 0.58 and diff_contraste >= 14.0)
        score = float(ratio_alternancia * (min(diff_contraste, 100.0) / 100.0))

        return score, es_valido

    def verificar_es_tablero(self, roi_bgr):
        """
        Chequeo rápido para confirmar si una ROI sigue siendo un tablero de ajedrez.
        """
        if roi_bgr is None or roi_bgr.size == 0:
            return False
        h, w = roi_bgr.shape[:2]
        if w < self.min_size or h < self.min_size:
            return False

        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY) if len(roi_bgr.shape) == 3 else roi_bgr
        std = float(np.std(gray))
        if std < 12.0:
            return False

        _, valido = self.calcular_score_damero(roi_bgr)
        return valido

    def _refinar_bordes(self, gray, x, y, w, h, margen=22):
        """Ajusta los bordes del recuadro al gradiente exterior exacto del tablero."""
        H, W = gray.shape
        # Borde Izquierdo
        x0, x1 = max(0, x - margen), min(W, x + margen)
        gx = np.abs(cv2.Sobel(gray[max(0, y):min(H, y+h), x0:x1], cv2.CV_32F, 1, 0, ksize=3))
        new_x = x0 + int(np.argmax(np.sum(gx, axis=0))) if x1 > x0 else x

        # Borde Superior
        y0, y1 = max(0, y - margen), min(H, y + margen)
        gy = np.abs(cv2.Sobel(gray[y0:y1, max(0, x):min(W, x+w)], cv2.CV_32F, 0, 1, ksize=3))
        new_y = y0 + int(np.argmax(np.sum(gy, axis=1))) if y1 > y0 else y

        # Borde Derecho
        xr0, xr1 = max(0, x + w - margen), min(W, x + w + margen)
        gxr = np.abs(cv2.Sobel(gray[max(0, y):min(H, y+h), xr0:xr1], cv2.CV_32F, 1, 0, ksize=3))
        new_x_right = xr0 + int(np.argmax(np.sum(gxr, axis=0))) if xr1 > xr0 else x + w

        # Borde Inferior
        yb0, yb1 = max(0, y + h - margen), min(H, y + h + margen)
        gyb = np.abs(cv2.Sobel(gray[yb0:yb1, max(0, x):min(W, x+w)], cv2.CV_32F, 0, 1, ksize=3))
        new_y_bottom = yb0 + int(np.argmax(np.sum(gyb, axis=1))) if yb1 > yb0 else y + h

        rw = new_x_right - new_x
        rh = new_y_bottom - new_y
        if rw >= self.min_size and rh >= self.min_size and 0.90 <= rw / float(rh) <= 1.10:
            return new_x, new_y, rw, rh
        return x, y, w, h

    def detectar_en_imagen(self, img_bgr, downscale=0.5):
        """
        Escanea una imagen completa (ej. pantalla 1920x1080) y localiza las coordenadas (x, y, w, h)
        del tablero de ajedrez más prometedor.
        """
        if img_bgr is None or img_bgr.size == 0:
            return None

        orig_h, orig_w = img_bgr.shape[:2]
        
        # Redimensionar para búsqueda rápida (< 20ms)
        small_w = int(orig_w * downscale)
        small_h = int(orig_h * downscale)
        small = cv2.resize(img_bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        
        # Detección de bordes y cierre morfológico (sin dilatación excesiva para no fusionar con barras de jugador)
        edges = cv2.Canny(gray, 30, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        candidatos = []
        min_sz_small = int(self.min_size * downscale)
        max_sz_small = int(self.max_size * downscale)

        for cnt in contours:
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw < min_sz_small or bh < min_sz_small:
                continue
            if bw > max_sz_small or bh > max_sz_small:
                continue

            ratio = bw / float(bh)
            if 0.88 <= ratio <= 1.14:
                # Convertir a resolución completa
                x = max(0, int(bx / downscale))
                y = max(0, int(by / downscale))
                w = min(orig_w - x, int(bw / downscale))
                h = min(orig_h - y, int(bh / downscale))

                # Ajustar a cuadrado simétrico
                dim = int((w + h) / 2.0)
                if x + dim <= orig_w and y + dim <= orig_h:
                    candidatos.append((x, y, dim, dim))
                else:
                    candidatos.append((x, y, w, h))

        # Evaluar candidatos y elegir el de mayor puntuación
        mejor_candidato = None
        mejor_score = 0.0

        # Eliminar duplicados cercanos
        candidatos_unicos = []
        for c in candidatos:
            cx, cy, cw, ch = c
            duplicado = False
            for ux, uy, uw, uh in candidatos_unicos:
                if abs(cx - ux) < 30 and abs(cy - uy) < 30 and abs(cw - uw) < 30:
                    duplicado = True
                    break
            if not duplicado:
                candidatos_unicos.append(c)

        for (cx, cy, cw, ch) in candidatos_unicos:
            roi = img_bgr[cy:cy+ch, cx:cx+cw]
            score, es_valido = self.calcular_score_damero(roi)
            if es_valido and score > mejor_score:
                mejor_score = score
                mejor_candidato = (cx, cy, cw, ch)

        if mejor_candidato is not None:
            # Refinar bordes en escala completa para máxima precisión
            orig_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            mx, my, mw, mh = mejor_candidato
            rx, ry, rw, rh = self._refinar_bordes(orig_gray, mx, my, mw, mh)
            return rx, ry, rw, rh

        return None

    def buscar_en_pantalla(self, sct, monitors):
        """
        Escanea la pantalla principal (Monitor 1) buscando el tablero de ajedrez.
        Retorna dict: {"top": int, "left": int, "width": int, "height": int} o None
        """
        # La pantalla de juego es siempre la pantalla principal
        mon = monitors[1] if len(monitors) > 1 else monitors[0]
        try:
            screenshot = sct.grab(mon)
            img = np.array(screenshot)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
            coords = self.detectar_en_imagen(img_bgr)
            if coords is not None:
                x, y, w, h = coords
                return {
                    "top": int(mon["top"] + y),
                    "left": int(mon["left"] + x),
                    "width": int(w),
                    "height": int(h)
                }
        except Exception:
            pass

        return None
