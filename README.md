# Chess Vision Assistant

Aplicación de escritorio para Windows que detecta tableros en pantalla, analiza posiciones de ajedrez y convierte errores de partidas guardadas en ejercicios. Usa OpenCV para reconocer las piezas, `python-chess` para validar jugadas y Stockfish para calcular evaluaciones y variantes. El motor se ejecuta localmente.

## Instalación

Necesitás Windows x86-64 y Python con Tkinter para el selector de archivos PGN. Desde la carpeta del proyecto, ejecutá estos comandos en PowerShell.

```powershell
python -m pip install pygame-ce python-chess opencv-python mss numpy
python -m chess_vision.herramientas.descargar_stockfish
python -m chess_vision.herramientas.descargar_piezas_hd
python -m chess_vision
```

La instalación guarda Stockfish y sus avisos en `datos_locales/stockfish/` y las imágenes en `recursos/piezas_hd/`.

## Revisar y practicar una partida

1. En el menú inicial, elegí **Abrir PGN** o pulsá **Ctrl + O**. Si el archivo contiene varias partidas, la app carga la primera.
2. Seleccioná **Blancas** o **Negras**. Stockfish compara tus jugadas con sus recomendaciones y muestra hasta tres caídas de evaluación de al menos medio peón, ordenadas por gravedad.
3. Elegí un error con los botones numerados. En el paso 0, la flecha naranja muestra tu jugada original y la verde indica la recomendación. Recorré la variante con **Anterior**, **Siguiente**, las flechas del teclado o la rueda del ratón.
4. Pulsá **Practicar** y dibujá tu intento con el botón derecho, desde la pieza hasta la casilla de destino. La app acepta alternativas con una evaluación similar y permite recorrer la continuación de la jugada elegida. También podés pulsar **Ver solución**.

Si jugaste en Chess.com, podés descargar el PGN de una partida terminada desde **Análisis → Compartir → PGN → Descargar**. [Guía de Chess.com](https://support.chess.com/en/articles/8705305-how-do-i-get-a-pgn-of-my-game)

## Capturar un tablero en pantalla

Para preparar la captura visual, dejá visible un tablero en posición inicial, con las blancas abajo, y ejecutá `python -m chess_vision.herramientas.aprender_piezas`. Si la detección automática no encuentra el tablero, ejecutá primero `python -m chess_vision.herramientas.calibrar_tablero` y seleccioná el área del tablero.

Abrí la interfaz y elegí el bando que corresponde a la orientación del tablero. La app replica la posición detectada, muestra la evaluación y dibuja la jugada recomendada cuando le toca mover a ese bando.

El modo de consola se inicia con `python -m chess_vision.interfaz.asistente_automatico`.

## Estructura del proyecto

- `chess_vision/interfaz/` contiene la interfaz gráfica y el modo de consola.
- `chess_vision/analisis/` contiene la revisión de PGN, el evaluador y el mentor.
- `chess_vision/captura/` contiene la detección del tablero y el seguimiento del ratón.
- `chess_vision/herramientas/` contiene los instaladores y las herramientas de calibración.
- `recursos/` y `datos_locales/` guardan imágenes, plantillas, configuración y el motor descargado.
- `docs/` y `tests/` contienen la documentación técnica y las pruebas.

El [flujo de desarrollo con Superpowers](docs/superpowers/plans/2026-11-10-flujo-superpowers.md) registra cómo se definieron, implementaron y verificaron la revisión PGN y las buenas alternativas.

## Pruebas

```powershell
python -B -m unittest discover -s tests -v
```
