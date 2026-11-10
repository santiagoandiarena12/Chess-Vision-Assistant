# In-App Side Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the console `input()` prompt on startup and replace it with an interactive in-app side selector in the Pygame panel that keeps the board visible while waiting for user selection before scanning begins.

**Architecture:** Introduce an app state (`SELECCIONANDO` vs `JUGANDO`) in `VisualChessApp`. While in `SELECCIONANDO`, the board renders in starting position, the worker thread idles without consuming CPU, and the panel displays interactive buttons (`[ ♔ BLANCAS ]` / `[ ♚ NEGRAS ]`). Clicks transition to `JUGANDO`, orient the board, and activate scanning.

**Tech Stack:** Python 3.14, Pygame-CE, python-chess, OpenCV

**Spec:** `docs/superpowers/specs/2026-11-05-in-app-side-selection-design.md`

## Global Constraints
- No terminal `input()` calls blocking startup in `__main__`.
- The chessboard must remain fully visible on screen while in the selection state.
- Zero CPU/vision polling load while waiting in `SELECCIONANDO`.
- Maintain existing Always-on-top and dynamic window resizing features.

## Review Focus
- Hover and click hitboxes must scale properly when the window is resized.
- Selecting Negras must flip the board and set `mi_color_str = "b"` correctly.
- Background vision thread must cleanly wake up once selection is made.
- Pressing `F` during a game must flip the board and allow re-selecting or toggling orientation.
- App exit via `ESC` or window close must work in both states without dangling threads.

---

### Task 1: Add State Machine and Interactive Button Logic to `VisualChessApp`

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- Produces: `self.estado_app` ("SELECCIONANDO" | "JUGANDO"), `self.btn_blancas_rect`, `self.btn_negras_rect`, `self.mouse_pos`

- [x] **Step 1: Define state attributes and button rectangles in `__init__` and `_recalcular_dimensiones`**
- [x] **Step 2: Add event handling for mouse clicks and mouse motion over the buttons**
- [x] **Step 3: Verify the state transitions properly when buttons are clicked**

---

### Task 2: Implement UI Rendering for the Selection State in `draw_panel`

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- Consumes: `self.estado_app`, `self.btn_blancas_rect`, `self.btn_negras_rect`

- [x] **Step 1: Implement selection UI card with ♔ BLANCAS and ♚ NEGRAS buttons in `draw_panel`**
- [x] **Step 2: Add visual hover feedback (color highlight) when cursor is over buttons**
- [x] **Step 3: Ensure layout dynamically responds to window resize (`_recalcular_dimensiones`)**

---

### Task 3: Integrate Background Vision Loop with App State and Remove Console Input

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- Consumes: `self.estado_app`, `self.juego_con_blancas`

- [x] **Step 1: Update `_background_vision_loop` to idle while `self.estado_app == "SELECCIONANDO"`**
- [x] **Step 2: Remove `input()` from `if __name__ == "__main__":` so the window opens directly**
- [x] **Step 3: Update `F` key handler to allow toggling or returning to selection if desired**

---

### Task 4: End-to-End Verification

**Files:**
- Test: `test_selector_state.py` (verification script)

- [x] **Step 1: Write verification script to test headless state transitions, button bounding boxes, and idle loop**
- [x] **Step 2: Execute verification script and confirm all checks pass**
- [x] **Step 3: Clean up temporary verification scripts and ensure clean compile**
