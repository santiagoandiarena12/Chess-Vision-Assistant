# Revisión y práctica de PGN

La app abrirá un archivo PGN desde el menú principal. El usuario elegirá el bando y recibirá hasta tres caídas de evaluación de esa partida. Cada posición mostrará la jugada original, la recomendación de Stockfish y una variante navegable. El botón **Practicar** devolverá el tablero a la posición original y ocultará la solución. Una flecha sobre el tablero permitirá intentar la jugada y recibir una devolución.

Se usará una pantalla dentro de Pygame, con el tablero, las piezas y el mentor existentes. Una ventana aparte duplicaría esos controles. Stockfish analizará el PGN en segundo plano con su propio proceso y la pantalla mostrará el progreso. Al salir, se cancelará el análisis y se liberará el motor.

El PGN será la fuente de las posiciones y sus reglas. Se analizará la primera partida de cada archivo y se mostrarán los tres errores con mayor pérdida de evaluación, o menos si no hay tres. El usuario podrá abrir otro archivo o volver al menú. El flujo funciona localmente.
