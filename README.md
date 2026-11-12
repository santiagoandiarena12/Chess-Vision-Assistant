# Chess Vision Assistant

Aplicación de escritorio para Windows que detecta tableros en pantalla, analiza posiciones de ajedrez y convierte errores de partidas guardadas en ejercicios. Usa OpenCV para reconocer las piezas, `python-chess` para validar jugadas y Stockfish para calcular evaluaciones y variantes. El motor se ejecuta localmente.

## Instalación

Necesitás Windows x86-64, Python con Tkinter para abrir archivos PGN y conexión a Internet para descargar las dependencias, Stockfish y las imágenes de las piezas.

Cloná el repositorio o descargalo desde **Code → Download ZIP** en GitHub y descomprimilo. Si usás Git, ejecutá estos comandos en PowerShell.

```powershell
git clone https://github.com/santiagoandiarena12/Chess-Vision-Assistant.git
cd Chess-Vision-Assistant
```

Desde la carpeta que contiene este README, creá un entorno virtual e instalá los componentes.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pygame-ce python-chess opencv-python mss numpy
.\.venv\Scripts\python.exe -m chess_vision.herramientas.descargar_stockfish
.\.venv\Scripts\python.exe -m chess_vision.herramientas.descargar_piezas_hd
```

La instalación guarda Stockfish y sus avisos en `datos_locales/stockfish/` y las imágenes en `recursos/piezas_hd/`.

Usá este comando desde esa misma carpeta para abrir la aplicación.

```powershell
.\.venv\Scripts\python.exe -m chess_vision
```

## Revisar y practicar una partida

Podés abrir un PGN apenas termina la instalación. La calibración y el aprendizaje de piezas se usan para capturar tableros en pantalla.

1. En el menú inicial, elegí **Abrir PGN** o pulsá **Ctrl + O**. Si el archivo contiene varias partidas, la app carga la primera.
2. Seleccioná **Blancas** o **Negras**. Stockfish compara tus jugadas con sus recomendaciones y muestra hasta tres caídas de evaluación de al menos medio peón, ordenadas por gravedad.
3. Elegí un error con los botones numerados. En el paso 0, la flecha naranja muestra tu jugada original y la verde indica la recomendación. Recorré la variante con **Anterior**, **Siguiente**, las flechas del teclado o la rueda del ratón.
4. Pulsá **Practicar** y dibujá tu intento con el botón derecho, desde la pieza hasta la casilla de destino. La app acepta alternativas con una evaluación similar y permite recorrer la continuación de la jugada elegida. También podés pulsar **Ver solución**.

Si jugaste en Chess.com, podés descargar el PGN de una partida terminada desde **Análisis → Compartir → PGN → Descargar**. [Guía de Chess.com](https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game)

## Capturar un tablero en pantalla

1. Dejá visible un tablero en posición inicial, con las blancas abajo. Usá el mismo tema de tablero y piezas que vas a usar durante la captura.
2. Ejecutá `.\.venv\Scripts\python.exe -m chess_vision.herramientas.aprender_piezas`. Tenés cuatro segundos para dejar el tablero a la vista. Las plantillas se guardan en `recursos/piezas/`.
3. Abrí la app y elegí **Blancas** si las blancas están abajo en el tablero externo, o **Negras** si las negras están abajo. La app replica la posición detectada y muestra la jugada recomendada cuando le toca mover a ese bando.

Si el aprendizaje no encuentra el tablero, mostralo en el monitor principal y ejecutá `.\.venv\Scripts\python.exe -m chess_vision.herramientas.calibrar_tablero`. En la captura, arrastrá un recuadro que cubra las 64 casillas y confirmá con **Enter** o **Espacio**. Después repetí el aprendizaje de piezas.

Para usar la captura desde la consola, ejecutá `.\.venv\Scripts\python.exe -m chess_vision.interfaz.asistente_automatico`. Elegí `w` para blancas o `b` para negras y pulsá **Ctrl + C** para salir.

## Estructura del proyecto

- `chess_vision/interfaz/` contiene la interfaz gráfica y el modo de consola.
- `chess_vision/analisis/` contiene la revisión de PGN, el evaluador y el mentor.
- `chess_vision/captura/` contiene la detección del tablero y el seguimiento del ratón.
- `chess_vision/herramientas/` contiene los instaladores y las herramientas de calibración.
- `recursos/` y `datos_locales/` guardan imágenes, plantillas, configuración y el motor descargado.
- `docs/` y `tests/` contienen la documentación técnica, guías de presentación, documentación del flujo Superpowers (`docs/superpowers/`) y las pruebas automatizadas.

## Pruebas

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```
