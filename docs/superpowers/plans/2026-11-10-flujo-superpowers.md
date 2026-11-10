# Flujo de desarrollo con Superpowers

Este registro explica cómo se diseñaron, implementaron y verificaron la revisión de partidas PGN y la práctica con varias respuestas. La secuencia se reconstruyó a partir de la conversación de desarrollo, las especificaciones, los planes y las pruebas.

## 1. Brainstorming

La conversación empezó con una pregunta sobre cómo mejorar Chess Vision Assistant y si convenía incorporar MCP o RAG. Se revisó lo que ya existía en la aplicación. Stockfish evaluaba posiciones, el mentor explicaba algunas jugadas y el tablero fantasma permitía recorrer variantes.

Se propusieron tres mejoras que aprovechaban ese punto de partida. La primera era importar un PGN y detectar los momentos decisivos. La segunda era convertir esos momentos en ejercicios. La tercera era permitir corregir el turno cuando la captura de pantalla resultara ambigua. También se conversó sobre MCP para consultar análisis desde un chat y RAG para incorporar material de estudio al mentor.

El usuario eligió **«Abrir PGN → revisar tres errores → practicar uno»**. El recorrido quedó definido como una pantalla dentro de la app de escritorio, con Stockfish local y los controles de tablero existentes. Esa elección en la conversación fue el punto de partida para escribir el diseño. [Guía de brainstorming de Superpowers](https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md)

## 2. Diseño y criterios de aceptación

Se definió que el usuario abriría un PGN, elegiría un bando y podría revisar hasta tres errores. La app cargaría la primera partida del archivo, compararía las jugadas desde la perspectiva del bando elegido y mostraría las caídas de al menos medio peón. La revisión presentaría la jugada original y la variante del motor. **Practicar** volvería a la posición inicial del ejercicio y ocultaría la solución hasta que el usuario encontrara una respuesta o decidiera revelarla.

La lógica de partidas y ejercicios se separó de la interfaz. El análisis se ejecutó en segundo plano para que la ventana pudiera seguir mostrando el progreso y responder a los controles. [Diseño de revisión PGN](../specs/2026-11-10-revision-pgn-design.md)

## 3. Plan de implementación

El trabajo se dividió en cuatro pasos verificables.

1. Escribir pruebas de lectura de PGN, selección de errores, recorrido de variantes y práctica.
2. Implementar la lectura de partidas, el análisis con Stockfish y el estado de cada ejercicio.
3. Conectar **Abrir PGN**, la selección de bando, la navegación y la práctica con flechas a la interfaz de Pygame.
4. Verificar la suite y recorrer el flujo completo con Stockfish real y eventos de interfaz simulados.

[Plan de revisión PGN](2026-11-10-revision-pgn.md) · [Guía de planificación de Superpowers](https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md)

## 4. Pruebas primero, implementación y ajustes

Las primeras pruebas fallaron al intentar importar el módulo de revisión, que todavía no existía. Después se implementó la lógica de lectura, comparación y práctica. La prueba de interfaz también empezó fallando al intentar abrir una sesión PGN, antes de que ese recorrido estuviera conectado. Con la implementación completa, pasaron las cuatro pruebas de esa etapa. [Guía de desarrollo con pruebas primero de Superpowers](https://github.com/obra/superpowers/blob/main/skills/test-driven-development/SKILL.md)

Durante el uso aparecieron dudas sobre el significado de los números, los colores de las flechas y el avance entre jugadas. Se incorporaron esas explicaciones directamente en el panel y se revisó que los controles y las leyendas entraran en una ventana de 600 × 420 píxeles.

## 5. Segunda iteración con MultiPV

En una conversación posterior se evaluaron otras funciones de Stockfish, como continuar una posición contra el motor, practicar mates o estudiar finales. El usuario eligió **aceptar varias buenas respuestas** en los ejercicios con flechas.

El diseño mantuvo una búsqueda de una sola línea para ordenar los errores. Para cada ejercicio seleccionado, Stockfish prepara hasta cinco líneas con MultiPV. Una alternativa se acepta si queda a una distancia máxima de 25 centipeones de la mejor evaluación. Los mates forzados se comparan aparte. Si el usuario prueba una jugada legal fuera de las variantes preparadas, se compara en segundo plano con la recomendación. La interfaz muestra la línea que empieza con la jugada aceptada.

Las pruebas iniciales detectaron que faltaban el análisis MultiPV y la comparación de intentos fuera de la lista. La prueba de interfaz detectó que todavía no se manejaba el resultado **«Buena alternativa»**. Luego se conectaron el análisis, la devolución y la navegación por la variante elegida. [Diseño de alternativas](../specs/2026-11-10-alternativas-pgn-design.md) · [Plan de alternativas](2026-11-10-alternativas-pgn.md)

## 6. Verificación antes de cerrar

- En la primera entrega se comprobó que era posible abrir un PGN de prueba, elegir el bando, revisar tres errores, practicar uno y volver al menú. Se usó Stockfish real y se simularon los eventos de Pygame y la selección del archivo.
- En la segunda entrega pasaron siete pruebas. Con Stockfish real también se comprobó que se podía recorrer una alternativa obtenida por MultiPV y aceptar un mate en uno que quedaba fuera de la lista preparada.
- Las verificaciones se hicieron en la sesión de implementación. Las pruebas automatizadas del repositorio se pueden repetir desde la raíz del proyecto.

```powershell
python -B -m unittest discover -s tests -v
```

[Pruebas de revisión](../../../tests/test_revision_pgn.py) · [Pruebas de interfaz](../../../tests/test_interfaz_revision_pgn.py) · [Guía de verificación de Superpowers](https://github.com/obra/superpowers/blob/main/skills/verification-before-completion/SKILL.md)
