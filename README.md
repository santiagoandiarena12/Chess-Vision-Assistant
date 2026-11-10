# Chess Vision Assistant

Aplicación de escritorio para Windows que analiza posiciones con Stockfish, detecta tableros en pantalla y convierte errores de partidas guardadas en ejercicios.

Desde la carpeta del proyecto, instalá las dependencias y prepará el motor y las imágenes del tablero.

```powershell
python -m pip install pygame-ce python-chess opencv-python mss numpy
python .\descargar_stockfish.py
python .\descargar_piezas_hd.py
python .\interfaz_visual.py
```

En **Abrir PGN**, elegí un archivo con una partida y seleccioná tu bando. La app muestra hasta tres errores con sus variantes. En **Practicar**, dibujá tu intento arrastrando con el botón derecho desde la pieza hasta la casilla de destino.

Para preparar la captura visual, dejá visible un tablero en posición inicial, con las blancas abajo, y ejecutá `python .\aprender_piezas.py`. Si la detección automática no encuentra el tablero, ejecutá primero `python .\calibrar_tablero.py` y seleccioná el área del tablero.

Para ejecutar las pruebas:

```powershell
python -B -m unittest discover -s tests -v
```
