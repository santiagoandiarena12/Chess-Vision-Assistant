# Plan de revisión de PGN

**Objetivo.** Abrir un PGN, revisar hasta tres errores de un bando y practicar una posición.

**Diseño.** `revision_pgn.py` procesa las partidas y administra la posición de revisión. `interfaz_visual.py` conecta esa lógica al menú, al tablero y al motor local. [Diseño](../specs/2026-11-10-revision-pgn-design.md)

- [x] Escribir pruebas de lectura de PGN, selección de los tres errores, navegación y práctica. Ejecutar `python -B -m unittest discover -s tests -v` y verificar el fallo por funcionalidad ausente.
- [x] Implementar `cargar_partida(ruta)`, `revisar_partida(partida, bando, motor, ...)` y `SesionRevision`. Validar PGN vacío, pérdidas comparadas desde el bando correcto y solución oculta durante la práctica. Volver a ejecutar la suite.
- [x] Agregar **Abrir PGN**, elección de bando, análisis cancelable, resultados y práctica con flechas. Compartir la ruta de Stockfish y el renderizado del tablero con la interfaz existente.
- [x] Verificar el flujo visual mediante eventos de Pygame, el análisis con el Stockfish incluido y la suite completa. Revisar manejo de errores, cancelación, orientación y posición de los controles.
