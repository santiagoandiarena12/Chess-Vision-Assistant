# Especificación de Diseño: Guía de Mate y Celebración de Victoria

**Fecha:** 2026-11-05  
**Objetivo:** Guiar al usuario hacia el remate de la partida (mostrando una cuenta regresiva de mate forzado en $X$ movimientos) y presentar un aviso de victoria sobrio, profesional y de alta calidad visual sobre el tablero y en el panel lateral al finalizar la partida.

---

## 1. Guía de Remate ("Camino al Mate")

Cuando Stockfish detecta una secuencia de jaque mate forzado (`score.is_mate()`):

### 1.1 Lógica de Cálculo
- Stockfish entrega `mate_score = score.white().mate()`:
  - Si el usuario tiene mate forzado ($N$ jugadas):
    - Se extrae $N = |\text{mate\_score}|$.
    - Estado: `es_mate_a_favor = True`, `mate_en = N`.
  - Si el rival tiene mate forzado:
    - Estado: `es_mate_a_favor = False`, `mate_en = N`.

### 1.2 Componente Visual en el Panel
- En lugar de mostrar solo el texto estándar, la tarjeta de jugada recomendada adopta un modo **Remate Táctico**:
  - **Insignia / Badge de Mate:**
    - A favor: `⚡ MATE EN N JUGADAS` con borde dorado sutil `(225, 185, 65)` y pulso suave de luminosidad.
    - En contra: `⚠️ AMENAZA DE MATE EN N` con acento ámbar.
  - **Texto explicativo:** "Sigue la secuencia para rematar la partida" (o "Defensa crítica requerida").
  - **Cuenta progresiva:** A medida que se juegan los movimientos, la cuenta desciende automáticamente ($3 \rightarrow 2 \rightarrow 1 \rightarrow \text{Mate}$).

---

## 2. Celebración de Victoria (Enfoque B)

Al alcanzarse el jaque mate en el tablero (`board.is_checkmate()`):

### 2.1 Cinta Translúcida sobre el Tablero (Estilo Lichess / Chess.com Studio)
- **Geometría y Fondo:**
  - Franja centrada horizontal y verticalmente sobre el tablero de ajedrez.
  - Alto: 100px; ancho: ancho completo del tablero con bordes redondeados (radio 10px).
  - Fondo: Superficie acrílica oscura translúcida `(22, 24, 30, 225)`.
  - Borde: 2px en dorado victoria `(225, 185, 65)` o verde esmeralda `(46, 204, 113)`.
- **Tipografía y Jerarquía:**
  - Título principal: `🏆 ¡VICTORIA!` (Segoe UI 28px negrita, blanco puro).
  - Subtítulo: `Jaque mate ejecutado con éxito • Partida finalizada` (Segoe UI 14px, gris plata suave).

### 2.2 Transformación del Panel Lateral
- La tarjeta de jugada recomendada cambia a **Tarjeta de Conclusión**:
  - Título: `PARTIDA FINALIZADA`
  - Resumen: Cantidad total de jugadas realizadas en el historial.
  - Botón interactivo: `[ ↺ Nueva Partida ]` (con hover visual) para reiniciar el estado y estar listo para el siguiente juego sin reiniciar la app.

### 2.3 Manejo de Tablas / Empate
- Si la partida termina por rey ahogado (`is_stalemate()`), material insuficiente o regla de 50 jugadas:
  - Cinta sobre el tablero: `⚖ TABLAS (EMPATE)`.
  - Subtítulo: `Posición de rey ahogado o material insuficiente`.

---

## 3. Principios Estéticos ("Anti-cliché de IA")

- **Tipografía nativa pulida:** Uso de Segoe UI con proporciones y espaciados armoniosos (sin emojis desalineados en texto simple).
- **Paleta de color refinada:**
  - Oro Victoria: `(225, 185, 65)`
  - Verde Esmeralda: `(46, 204, 113)`
  - Fondo Translúcido: `(22, 24, 30, 225)`
  - Texto Principal: `(245, 245, 250)`
  - Texto Secundario: `(170, 175, 190)`
- **Animación:** Pulso sutil y pausado en el resplandor de la insignia de mate (sin parpadeos rápidos ni destellos molestos).

---

## 4. Archivos a Modificar
- **`asistente.py`:**
  - Enriquecer `obtener_mejor_jugada` para retornar un dict estructurado:
    `{"move": move, "eval_str": eval_str, "mate_in": N, "is_mate": bool, "mate_for_me": bool}`.
- **`interfaz_visual.py`:**
  - Añadir soporte a `self.state["mate_in"]` y `self.state["game_over_state"]`.
  - Crear método `draw_victory_banner()` sobre el tablero.
  - Actualizar `draw_panel()` con la insignia de mate forzado y el botón `[ ↺ Nueva Partida ]`.
