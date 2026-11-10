# Especificación de Diseño: Modo Mentor, Tablero Fantasma y Celebración de Victoria

**Fecha:** 2026-11-05  
**Objetivo:** Integrar una experiencia de usuario interactiva y elegante que combina:
1. **Modo Mentor:** Explicaciones conceptuales automáticas de por qué se recomienda cada jugada (capturas, clavadas, tenedores, columnas abiertas, puestos avanzados, seguridad de rey).
2. **Tablero Fantasma (Future Scroller):** Previsualización interactiva de la variante principal (línea de 3 a 4 movimientos futuros de Stockfish) navegable con la rueda del ratón o teclas `←` `→`.
3. **Guía de Mate y Celebración de Victoria:** Cuenta regresiva táctica de mate forzado y cinta translúcida acrílica sobre el tablero al ganar.

---

## 1. Arquitectura y Componentes

### 1.1 Motor Conceptual del "Modo Mentor" (`mentor_ajedrez.py`)
Un módulo desacoplado que analiza la jugada recomendada `best_move` sobre el tablero `board` y la línea `pv` (Principal Variation) de Stockfish:
- **Táctica directa:**
  - *Jaque:* Si `board.gives_check(move)` $\rightarrow$ `"Jaque forzado al rey rival"`.
  - *Captura con ganancia:* Si captura pieza de mayor o igual valor $\rightarrow$ `"Gana [Dama/Torre/Alfil/Caballo/Peón] en [Casilla]"`.
  - *Tenedor / Doble ataque:* Si la pieza atacará a $\ge 2$ piezas rivales $\rightarrow$ `"Ataque doble (tenedor) a [Pieza A] y [Pieza B]"`.
  - *Clavada:* Si restringe una pieza rival contra el rey o la dama $\rightarrow$ `"Clava la pieza rival contra la dama/rey"`.
- **Estrategia y Posición:**
  - *Enroque / Seguridad:* Si es enroque $\rightarrow$ `"Protege al rey y conecta las torres"`.
  - *Columna abierta:* Si una torre se mueve a una columna sin peones $\rightarrow$ `"Domina la columna abierta [col]"`.
  - *Puesto avanzado:* Caballo central defendido por peón $\rightarrow$ `"Instala el caballo en un puesto avanzado en [sq]"`.
  - *Invasión de 7ª fila:* Torre en 7ª fila $\rightarrow$ `"Invade la 7ª fila atacando la base de peones"`.
  - *Desarrollo / Centro:* Si mueve peón o pieza menor en apertura $\rightarrow$ `"Controla el centro y activa piezas"`.
  - *Defensa:* Si la casilla de destino defiende una pieza amenazada $\rightarrow$ `"Defiende la pieza amenazada en [sq]"`.

### 1.2 "Tablero Fantasma" (Interactive Ghost Board)
- **Extracción de la variante:** Stockfish entrega `info["pv"]` (lista de 3 a 5 jugadas consecutivas `[m1, m2, m3, m4]`).
- **Estado de Navegación en `VisualChessApp`:**
  - `self.ghost_step`: entero de `0` a `len(pv)` (donde `0` = posición en vivo real en pantalla).
  - Al girar la rueda del ratón (`pygame.MOUSEWHEEL`) sobre el tablero o presionar `pygame.K_LEFT` / `pygame.K_RIGHT`:
    - `ghost_step = max(0, min(max_steps, ghost_step + delta))`
- **Renderizado Visual del Tablero Fantasma (`ghost_step > 0`):**
  - Las piezas que se han movido en la variante se dibujan con un resplandor translúcido suave (alfa 190-210) y un sutil borde indicador.
  - La flecha de movimiento apunta a la jugada de ese paso específico (verde para jugada nuestra, naranja para réplica del rival).
  - **Insignia flotante superior:** `👻 FUTURO: Jugada +N • [m_uci] (Gira la rueda o pulsa ESC/0 para volver)`.
  - Al llegar un nuevo movimiento en vivo en la pantalla real, `ghost_step` se resetea automáticamente a `0` para nunca desincronizarse de la partida en curso.

### 1.3 Guía de Mate y Celebración de Victoria
- **Insignia de Mate Forzado:**
  - Cuando `mate_in` está activo: píldora dorada/esmeralda `⚡ MATE EN N JUGADAS` con pulso de luz pausado.
- **Cinta de Victoria Translúcida:**
  - Al producirse el jaque mate (`board.is_checkmate()`):
    - Franja centrada en el tablero con fondo acrílico oscuro `(22, 24, 30, 225)` y borde dorado `(225, 185, 65)`.
    - Texto principal: `🏆 ¡VICTORIA POR JAQUE MATE!`
    - Subtítulo: `Partida finalizada con éxito • [N] jugadas registradas`
  - Botón en el panel: `[ ↺ Nueva Partida ]` que resetea el historial y prepara el asistente para el siguiente juego sin reiniciar.

---

## 2. Experiencia de Usuario y Diseño Visual (UI/UX)

- **Anti-cliché de IA:** Sin emojis genéricos mal alineados ni colores fluorescentes estridentes.
- **Tipografía y Proporciones:**
  - Píldora de idea conceptual: Segoe UI 13px con ícono geométrico estilizado (`💡 Idea: Clava el caballo a la dama`).
  - Navegación fantasma: Micro-indicador de 3 bolitas interactivas `[ ● ○ ○ ]` en la tarjeta de jugada.
- **Paleta de Colores:**
  - Oro Victoria: `(225, 185, 65)`
  - Verde Esmeralda: `(46, 204, 113)`
  - Naranja Réplica Rival: `(235, 140, 50)`
  - Superficie Translúcida: `(24, 27, 34, 230)`
  - Texto Principal: `(245, 245, 250)`

---

## 3. Plan de Archivos
- **Crear `mentor_ajedrez.py`:** Generador de explicaciones tácticas y conceptuales de ajedrez.
- **Modificar `asistente.py`:** Retornar la línea `pv` completa (variante de 3 a 5 jugadas) y datos de mate forzado.
- **Modificar `interfaz_visual.py`:**
  - Manejo de eventos de rueda de ratón (`pygame.MOUSEWHEEL`) y flechas teclado (`K_LEFT`, `K_RIGHT`).
  - Renderizado de píldora de Modo Mentor en `draw_panel()`.
  - Renderizado de piezas translúcidas y banner en `draw_board()`.
  - Cinta de victoria sobre el tablero al detectar mate.
