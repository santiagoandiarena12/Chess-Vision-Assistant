# Mentor Mode, Ghost Board & Victory Announcements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate "Modo Mentor" (tactical conceptual explanations for moves), "Tablero Fantasma" (interactive future move scroller with mouse wheel / arrows), and "Celebración de Victoria" (translucent acrylic ribbon on checkmate and mate-in-N countdown).

**Architecture:** A dedicated `mentor_ajedrez.py` module inspects board tactics (pins, forks, checks, captures, open files, castling) to generate clean Spanish explanations. `asistente.py` extracts the full Principal Variation (`pv`) from Stockfish. `interfaz_visual.py` adds wheel/arrow navigation, ghost piece rendering, mentor badges, and the victory ribbon.

**Tech Stack:** Python 3.14, Pygame-CE, python-chess, OpenCV, NumPy, Stockfish

**Spec:** `docs/superpowers/specs/2026-11-05-mentor-mode-ghost-board-design.md`

## Global Constraints
- Zero terminal `input()` calls.
- Preserves accurate piece recognition and fast live scanning (~2ms ROI, ~10Hz).
- Resets ghost view to step 0 automatically when a live move arrives on screen.
- High visual aesthetics: Segoe UI typography, gold/emerald accents, acrylic translucent surfaces, anti-cliché AI design.

## Review Focus
- Scrolling mouse wheel over the board must cycle steps smoothly (0 = live, 1..4 = future moves).
- Mentor explanation must correctly identify pins, forks, hanging pieces, and checks.
- Checkmate on board must trigger the victory banner and show `[ ↺ Nueva Partida ]`.
- Resizing the window must scale the ghost banner and victory ribbon without clipping.
- No memory leaks or performance degradation from ghost cloning.

---

### Task 1: Create `mentor_ajedrez.py` (Tactical Conceptual Explanations Engine)

**Files:**
- Create: `mentor_ajedrez.py`
- Test: `test_mentor_ajedrez.py`

**Interfaces:**
- `explicar_jugada(board: chess.Board, move: chess.Move) -> str`

- [ ] **Step 1: Write failing unit test `test_mentor_ajedrez.py` with known tactical positions (fork, pin, check, capture, castling)**
- [ ] **Step 2: Implement `explicar_jugada` in `mentor_ajedrez.py` with tactical rules**
- [ ] **Step 3: Run `test_mentor_ajedrez.py` and confirm all tests pass**

---

### Task 2: Extend `asistente.py` with Principal Variation (`pv`) and Mate Extraction

**Files:**
- Modify: `asistente.py`

**Interfaces:**
- `obtener_mejor_jugada(fen, tiempo_analisis=0.3) -> dict(move, eval_str, mate_in, pv_moves, idea)`

- [ ] **Step 1: Update `obtener_mejor_jugada` to extract `pv` line and mate score from Stockfish**
- [ ] **Step 2: Integrate `mentor_ajedrez.explicar_jugada` into the returned dictionary**
- [ ] **Step 3: Run unit test confirming rich analysis dictionary is returned**

---

### Task 3: Implement "Tablero Fantasma" (Interactive Future Scroller) in `interfaz_visual.py`

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- `self.ghost_step` (int)
- Event handlers: `pygame.MOUSEWHEEL`, `pygame.K_LEFT`, `pygame.K_RIGHT`
- `draw_ghost_banner()` and ghost piece rendering with alpha aura in `draw_board()`

- [ ] **Step 1: Add `self.ghost_step` state and event handling for wheel and arrow keys**
- [ ] **Step 2: Implement ghost board state derivation from `pv_moves`**
- [ ] **Step 3: Implement translucent ghost piece rendering and top notification badge in `draw_board()`**

---

### Task 4: Implement "Modo Mentor" Badge and Mate Countdown in `draw_panel()`

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- Consumes: `self.state["mentor_idea"]`, `self.state["mate_in"]`
- Renders: Idea pill with icon (`💡 Idea: ...`) and Mate badge (`⚡ MATE EN N JUGADAS`)

- [ ] **Step 1: Add `mentor_idea` and `mate_in` to `self.state`**
- [ ] **Step 2: Render stylized Idea badge and pulsing Mate countdown in `draw_panel()`**
- [ ] **Step 3: Render micro step navigator `[ ● ○ ○ ]` for ghost board in panel**

---

### Task 5: Implement Victory Ribbon and End of Game Banner

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- `draw_victory_ribbon(title, subtitle, is_victory)`
- Interactive button `[ ↺ Nueva Partida ]` in panel on game over

- [ ] **Step 1: Implement `draw_victory_ribbon()` with acrylic background and gold/emerald border**
- [ ] **Step 2: Add game over detection (`is_checkmate()`, `is_stalemate()`) in `_background_vision_loop`**
- [ ] **Step 3: Add `[ ↺ Nueva Partida ]` button in panel to reset board and state seamlessly**

---

### Task 6: End-to-End Verification

**Files:**
- Test: `test_e2e_features.py`

- [ ] **Step 1: Write headless test testing mentor explanations, ghost scrolling, and victory ribbon**
- [ ] **Step 2: Run verification test and confirm PASS**
- [ ] **Step 3: Clean up test scripts and verify compilation across all modules**
