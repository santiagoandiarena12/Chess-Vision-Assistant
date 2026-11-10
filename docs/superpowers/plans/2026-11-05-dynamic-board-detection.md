# Dynamic Board Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically detect the chessboard anywhere on screen across any platform (Chess.com, Lichess, desktop) and dynamically track it when moved or resized, eliminating manual ROI cropping.

**Architecture:** A dedicated `DetectorTablero` module uses contour geometry, grid line periodicity, and 8×8 checkerboard cell parity correlation to find boards in screenshots. Integrated into `AsistenteAjedrez` with a dual-state "Smart Lock & Track" engine (fast 2ms ROI capture while locked, 25ms full-screen scan when lost or searching). `VisualChessApp` displays real-time lock status in the panel.

**Tech Stack:** Python 3.14, OpenCV (cv2), NumPy, MSS, Pygame-CE, python-chess

**Spec:** `docs/superpowers/specs/2026-11-05-dynamic-board-detection-design.md`

## Global Constraints
- Must be platform-agnostic (works on Chess.com, Lichess, desktop apps, any board theme/colors).
- Zero terminal `input()` calls.
- High-efficiency: locked state must only capture the board ROI (~2ms); full-screen discovery must run in under 35ms.
- Graceful degradation: if no board is open, display `◌ BUSCANDO TABLERO...` without crashing or freezing Pygame.
- Multi-monitor support: scans the primary monitor by default and checks connected monitors if not found.

## Review Focus
- Resizing or moving the browser window must cause auto-relocalization within 1 second.
- Highlighted move squares (yellow/green) and pieces on the board must not prevent checkerboard detection.
- Non-square rectangular windows or non-chess images must be rejected by the 8×8 parity filter.
- Low CPU overhead when locked in normal gameplay.
- Seamless fallback if no chessboard is visible on screen.

---

### Task 1: Create `detector_tablero.py` with 8×8 Checkerboard Parity & Geometry Filter

**Files:**
- Create: `detector_tablero.py`
- Test: `test_detector_tablero.py`

**Interfaces:**
- `DetectorTablero.detectar_en_imagen(img_bgr, downscale=0.5) -> (x, y, w, h) | None`
- `DetectorTablero.verificar_es_tablero(roi_bgr) -> bool`
- `DetectorTablero.buscar_en_pantalla(sct, monitors) -> dict(top, left, width, height) | None`

- [x] **Step 1: Write `test_detector_tablero.py` testing detection on existing board image and rejection on plain image**
- [x] **Step 2: Implement `DetectorTablero` class in `detector_tablero.py`**
- [x] **Step 3: Run `test_detector_tablero.py` and verify all tests pass**

---

### Task 2: Integrate Dynamic Tracker into `AsistenteAjedrez` in `asistente.py`

**Files:**
- Modify: `asistente.py`

**Interfaces:**
- `AsistenteAjedrez.estado_tracker` ("ENGANCHADO" | "BUSCANDO")
- `AsistenteAjedrez.obtener_captura_tablero()` -> `np.ndarray | None`
- `AsistenteAjedrez.actualizar_coordenadas(nuevas_coords)`

- [x] **Step 1: Add `self.detector` and tracker state management in `AsistenteAjedrez.__init__`**
- [x] **Step 2: Update `capturar_tablero()` to perform fast verification and auto-relocalization on demand**
- [x] **Step 3: Add unit test verifying auto-relocalization when simulated coordinates drift**

---

### Task 3: Update `interfaz_visual.py` to Display Tracking Status

**Files:**
- Modify: `interfaz_visual.py`

**Interfaces:**
- Consumes: `asistente.estado_tracker`, `asistente.coordenadas`
- Renders: Tracker badge in side panel (Verde `● ENGANCHADO` o Amarillo `◌ BUSCANDO`)

- [x] **Step 1: Add tracker status to `self.state` in `interfaz_visual.py`**
- [x] **Step 2: Render tracker badge in `draw_panel()`**
- [x] **Step 3: Handle `captura is None` gracefully in `_background_vision_loop` without raising exceptions**

---

### Task 4: End-to-End Verification

**Files:**
- Test: `test_e2e_tracker.py`

- [x] **Step 1: Create verification script testing full cycle: discovery -> lock -> drift -> auto-re-lock**
- [x] **Step 2: Run verification script and confirm PASS**
- [x] **Step 3: Clean up test scripts and run compilation check on all python files**
