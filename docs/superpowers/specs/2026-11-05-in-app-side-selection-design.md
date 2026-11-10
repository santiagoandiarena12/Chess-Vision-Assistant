# Diseño Corto: Selector de Bando Gráfico dentro de la App

## 1. Intención y Objetivo
Eliminar la solicitud por consola (`input()` en PowerShell) al arrancar `interfaz_visual.py`. La app debe abrir la ventana gráfica de Pygame de inmediato con el tablero visible de fondo, pero pausada hasta que el usuario seleccione interactivamente si juega con Blancas o Negras mediante botones en el panel lateral.

## 2. Enfoques Considerados

### Enfoque 1: Pantalla modal / Popup bloqueante inicial
- **Descripción:** Una pantalla o popup que tapa el tablero hasta que se hace clic en Blancas o Negras.
- **Desventaja:** El usuario solicitó explícitamente ver el tablero de fondo desde el inicio.

### Enfoque 2: Máquina de estados en el Panel Lateral (Seleccionado)
- **Descripción:** El tablero se renderiza completo en posición inicial. El panel lateral arranca en estado `ESPERANDO_BANDO` mostrando dos botones clickeables (`[ ♔ BLANCAS ]` y `[ ♚ NEGRAS ]`). El hilo de escaneo en segundo plano no procesa movimientos hasta que el usuario hace clic. Al hacer clic, pasa a `JUGANDO`, orienta el tablero y activa el motor.
- **Ventaja:** Cumple al 100% el requerimiento sin tapar el tablero y con una estética integrada y limpia.

## 3. Especificación de Cambios

1. **`__main__` en `interfaz_visual.py`:**
   - Eliminar `input("¿Juegas con Blancas (w) o Negras (b)?...")`.
   - Inicializar `VisualChessApp()` directamente sin parámetros requeridos en consola.

2. **Estados en `VisualChessApp`:**
   - `self.estado_app = "SELECCIONANDO"` (inicial) vs `"JUGANDO"`.
   - `self.juego_con_blancas = None` al inicio.
   - Rectángulos interactivos para los botones de selección: `self.btn_blancas_rect` y `self.btn_negras_rect`.

3. **Manejo de Eventos (`run`):**
   - Capturar `pygame.MOUSEBUTTONDOWN` y `pygame.MOUSEMOTION` para hover y clic en los botones.
   - Al pulsar un botón:
     - Establecer `self.juego_con_blancas` (True o False).
     - Actualizar `self.state["flip"]` (si es Negras, `flip = True`).
     - Cambiar `self.estado_app = "JUGANDO"`.
     - Activar el hilo de escaneo.
   - Permitir pulsar la tecla `F` o un botón pequeño `[Cambiar Bando]` para volver a seleccionar en cualquier momento.

4. **Renderizado del Panel (`draw_panel`):**
   - Si `self.estado_app == "SELECCIONANDO"`: dibujar tarjeta "ELIGE TU BANDO" con los dos botones con efecto hover.
   - Si `self.estado_app == "JUGANDO"`: dibujar la interfaz actual (tarjeta de mejor jugada, historial, turno).

5. **Hilo de Visión (`_background_vision_loop`):**
   - En cada ciclo, si `self.estado_app == "SELECCIONANDO"`, hacer `time.sleep(0.1)` y esperar sin consumir recursos ni escanear.
