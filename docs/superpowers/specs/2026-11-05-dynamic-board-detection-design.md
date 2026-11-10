# Especificación de Diseño: Detección Automática y Seguimiento Dinámico del Tablero

**Fecha:** 2026-11-05  
**Objetivo:** Permitir que el Asistente de Ajedrez localice automáticamente el tablero en pantalla (en cualquier plataforma: Chess.com, Lichess, aplicaciones de escritorio, etc.) y rastree dinámicamente su posición si la ventana es movida o redimensionada, eliminando la necesidad de calibración o recorte manual con `calibrar_tablero.py`.

---

## 1. Algoritmo de Detección Universal (Agnóstico de Plataforma)

Un tablero de ajedrez en cualquier sitio web o aplicación tiene propiedades visuales invariantes:
1. **Geometría cuadrada:** Ratio de aspecto `ancho / alto ≈ 1.0` (tolerancia 0.96 a 1.04).
2. **Tamaño sustancial:** Ancho y alto de entre 260px y 1100px.
3. **Filtro de Dameros 8×8 (Correlación Checkerboard):**
   - El candidato se sub-divide en una cuadrícula virtual de 8 filas × 8 columnas.
   - Se calcula el brillo medio interior de cada una de las 64 casillas.
   - Se compara con la máscara checkerboard canónica:
     $$M(r, c) = (r + c) \pmod 2$$
   - La correlación de alternancia entre casillas claras y oscuras debe superar un umbral robusto (> 0.65), aun con piezas o resaltados presentes.
4. **Validación de Líneas de Cuadrícula (Gradientes / Sobel):**
   - Los bordes a distancias periódicas de $1/8, 2/8, \dots, 7/8$ presentan picos de gradiente consistentes a lo largo de los ejes vertical y horizontal.

---

## 2. Estrategia de Rendimiento: "Smart Lock & Track"

Buscar en toda la resolución de pantalla a 10 fotogramas por segundo saturaría un núcleo de la CPU. Por ello, el sistema opera con dos modos automáticos:

1. **Modo ENGANCHADO (Locked):**
   - MSS sólo captura el área recortada del tablero `(left, top, width, height)`.
   - Tiempo de captura: ~2 ms. Consumo de CPU: insignificante.
   - En cada fotograma verifica un "Health Check" rápido: confirma que el contraste 8x8 sigue presente.
2. **Modo BÚSQUEDA / RE-ENGANCHE (Auto-Discovery):**
   - Se activa al iniciar la app o si el "Health Check" falla (cuando el usuario mueve, minimiza o cambia de pestaña la ventana del navegador).
   - Escanea la pantalla completa escalada a 50% para localizar el tablero en menos de 25 ms.
   - Frecuencia de reintento si no lo encuentra: 1 vez por segundo (no bloquea el hilo principal ni la fluidez de Pygame).

---

## 3. Impacto en la Interfaz Visual

- **Indicador de Estado en el Panel:**
  - `● TABLERO ENGANCHADO` (Verde) con las coordenadas dinámicas.
  - `◌ BUSCANDO TABLERO...` (Amarillo) si no hay ningún tablero visible en pantalla.
- **Transparencia total:** El usuario no necesita abrir `calibrar_tablero.py` ni arrastrar cajas con el ratón. Simplemente abre Chess.com y la app se vincula sola.
- **Fallback manual preservado:** Las coordenadas guardadas en `coordenadas.json` se usan como pista inicial de búsqueda antes de hacer barrido completo.

---

## 4. Archivos a Modificar / Crear

1. **`detector_tablero.py` (Nuevo módulo):**
   - Función `detectar_tablero_en_pantalla(img_screen)` -> `(x, y, w, h)` o `None`.
   - Función `verificar_es_tablero(roi_bgr)` -> `bool` (chequeo rápido de persistencia).
2. **`asistente.py`:**
   - Integrar `DetectorTablero` en el ciclo de captura.
   - Si la posición actual es válida, captura ROI; si se descalibra, invoca re-detección automática.
3. **`interfaz_visual.py`:**
   - Mostrar estado del tracker (`Buscando...` vs `Enganchado`) en el panel lateral.
