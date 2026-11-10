import os
import time
import winsound
import chess
import chess.engine
from asistente import AsistenteAjedrez

def reproducir_aviso():
    """Emite un pequeño pitido agradable cuando es tu turno."""
    try:
        winsound.Beep(1000, 150)
    except Exception:
        pass

def modo_automatico():
    print("=" * 65)
    print("      ASISTENTE DE AJEDREZ EN VIVO (MODO AUTOMÁTICO)")
    print("=" * 65)
    print("Detecta automáticamente cada jugada del rival sin tocar teclas.")
    print("-" * 65)

    bando = input("¿Juegas con Blancas o Negras? [w/b] (por defecto: w): ").strip().lower()
    mi_color = chess.BLACK if bando == "b" else chess.WHITE
    nombre_bando = "Blancas" if mi_color == chess.WHITE else "Negras"
    
    print(f"\n[OK] Jugando con: {nombre_bando}")
    print("Iniciando escaneo continuo en segundo plano...")
    print("Presiona Ctrl + C en cualquier momento para detener.\n")

    asistente = AsistenteAjedrez(orientacion_blancas=(mi_color == chess.WHITE))
    
    # Tablero lógico interno
    partida = chess.Board()
    ultimo_fen_cuerpo = None
    ultimo_analisis_fen = None

    # Si jugamos con blancas y estamos al inicio, dar primera sugerencia
    if mi_color == chess.WHITE:
        jugada_inicial, ev = asistente.obtener_mejor_jugada(partida.fen())
        if jugada_inicial:
            print(f">>> ES TU TURNO ({nombre_bando})")
            print(f">>> MEJOR JUGADA INICIAL: {str(jugada_inicial)[:2].upper()} -> {str(jugada_inicial)[2:4].upper()} ({jugada_inicial})")
            print(f">>> Ventaja: {ev}")
            print("-" * 55)

    while True:
        try:
            time.sleep(0.4) # Escanear cada 400ms (muy bajo consumo de CPU)
            
            # 1. Capturar pantalla y obtener FEN actual
            casillas, _ = asistente.detector.obtener_casillas(orientacion_blancas=(mi_color == chess.WHITE))
            fen_actual, matriz = asistente.generar_fen(casillas, turno="w" if partida.turn == chess.WHITE else "b")
            cuerpo_actual = fen_actual.split()[0]

            # Si el tablero visual no ha cambiado, no hacer nada
            if cuerpo_actual == ultimo_fen_cuerpo:
                continue

            # Pausa de 250ms para asegurar que la animación de la pieza terminó
            time.sleep(0.25)
            casillas, _ = asistente.detector.obtener_casillas(orientacion_blancas=(mi_color == chess.WHITE))
            fen_actual, matriz = asistente.generar_fen(casillas, turno="w" if partida.turn == chess.WHITE else "b")
            cuerpo_actual = fen_actual.split()[0]

            # 2. Verificar si coincide con una jugada legal del tablero interno
            movimiento_encontrado = None
            for jugada_posible in partida.legal_moves:
                partida.push(jugada_posible)
                if partida.board_fen() == cuerpo_actual:
                    movimiento_encontrado = jugada_posible
                    break
                partida.pop()

            # Si no coincide (ej: reset de partida o desincronización), sincronizar tablero
            if not movimiento_encontrado:
                try:
                    partida_tentativa = chess.Board(fen_actual)
                    if partida_tentativa.is_valid():
                        partida = partida_tentativa
                        ultimo_fen_cuerpo = cuerpo_actual
                except Exception:
                    pass
            else:
                ultimo_fen_cuerpo = cuerpo_actual
                quien_movio = "El rival" if partida.turn == mi_color else "Tú"
                origen = str(movimiento_encontrado)[:2].upper()
                destino = str(movimiento_encontrado)[2:4].upper()
                print(f"[{quien_movio} jugó]: {origen} -> {destino}")

            # 3. ¿Es nuestro turno para jugar?
            if partida.turn == mi_color and cuerpo_actual != ultimo_analisis_fen:
                reproducir_aviso()
                jugada, evaluacion = asistente.obtener_mejor_jugada(partida.fen(), tiempo_analisis=0.4)
                
                if jugada:
                    ultimo_analisis_fen = cuerpo_actual
                    orig = str(jugada)[:2].upper()
                    dest = str(jugada)[2:4].upper()
                    
                    print("\n" + "=" * 55)
                    print(f">>> ¡TU TURNO! ({nombre_bando})")
                    print(f">>> MEJOR JUGADA RECOMENDADA: {orig} -> {dest} ({jugada})")
                    print(f">>> Evaluación Stockfish: {evaluacion}")
                    print("=" * 55 + "\n")
                else:
                    print(f"[!] No se pudo calcular jugada: {evaluacion}")

        except KeyboardInterrupt:
            print("\n[OK] Asistente automático detenido.")
            break
        except Exception as e:
            # Continuar en el siguiente ciclo si hay error transitorio
            time.sleep(0.5)

if __name__ == "__main__":
    modo_automatico()
