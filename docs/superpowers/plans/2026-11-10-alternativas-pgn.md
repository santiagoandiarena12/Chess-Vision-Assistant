# Plan de buenas alternativas en PGN

**Objetivo.** Aceptar respuestas de evaluación similar y mostrar cómo sigue la línea elegida. [Diseño](../specs/2026-11-10-alternativas-pgn-design.md)

El [registro del flujo con Superpowers](2026-11-10-flujo-superpowers.md#5-segunda-iteración-con-multipv) explica cómo se eligió MultiPV y cómo se comprobó el recorrido completo.

- [x] Verificar primero que las pruebas detectan la ausencia de MultiPV, el filtro de puntuación desde el bando correcto y la falta de navegación por la variante del intento.
- [x] Preparar variantes con MultiPV, comparar jugadas fuera de la lista y guardar la línea aceptada en `SesionRevision`.
- [x] Reutilizar el trabajo en segundo plano en `interfaz_visual.py`. Mostrar la confirmación y la variante del intento, y cancelar el trabajo al cambiar de posición.
- [x] Ejecutar `python -B -m unittest discover -s tests -v` y verificar una búsqueda MultiPV con Stockfish real.
