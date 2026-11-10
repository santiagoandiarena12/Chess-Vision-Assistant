import chess

NOMBRES_PIEZAS = {
    chess.PAWN: "peón",
    chess.KNIGHT: "caballo",
    chess.BISHOP: "alfil",
    chess.ROOK: "torre",
    chess.QUEEN: "dama",
    chess.KING: "rey"
}

VALORES_PIEZAS = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 100
}

def explicar_jugada(board: chess.Board, move: chess.Move) -> str:
    """
    Analiza una jugada en un tablero de ajedrez y genera una explicación
    conceptual, táctica y humana en español.
    """
    if move is None or not board.is_legal(move):
        return "Movimiento táctico calculado"

    pieza_movida = board.piece_at(move.from_square)
    if pieza_movida is None:
        return "Movimiento táctico calculado"

    tipo_pieza = pieza_movida.piece_type
    nombre_pieza = NOMBRES_PIEZAS.get(tipo_pieza, "pieza")
    color = pieza_movida.color
    color_rival = not color
    to_sq_name = chess.square_name(move.to_square).upper()

    # 1. Enroque
    if board.is_castling(move):
        lado = "corto" if chess.square_file(move.to_square) == 6 else "largo"
        return f"Asegura el rey mediante enroque {lado}"

    # 2. Promoción
    if move.promotion:
        return f"Corona el peón en {to_sq_name} a nueva dama"

    # Tablero resultante
    b_next = board.copy()
    b_next.push(move)

    # 3. Jaque mate
    if b_next.is_checkmate():
        return f"¡Jaque mate definitivo con {nombre_pieza} en {to_sq_name}!"

    # 4. Jaque directo
    if board.gives_check(move):
        return f"Jaque forzado al rey rival con {nombre_pieza} en {to_sq_name}"

    # 5. Capturas
    if board.is_capture(move):
        tipo_capturada = board.piece_type_at(move.to_square)
        if tipo_capturada is None and board.is_en_passant(move):
            tipo_capturada = chess.PAWN
        
        nombre_cap = NOMBRES_PIEZAS.get(tipo_capturada, "pieza")
        defensores = board.attackers(color_rival, move.to_square)
        if not defensores:
            return f"Gana {nombre_cap} indefensa en {to_sq_name}"
        else:
            val_movida = VALORES_PIEZAS.get(tipo_pieza, 1)
            val_cap = VALORES_PIEZAS.get(tipo_capturada, 1)
            if val_cap > val_movida:
                return f"Gana calidad capturando {nombre_cap} con {nombre_pieza}"
            return f"Captura {nombre_cap} rival en {to_sq_name}"

    # 6. Ataque Doble / Tenedor
    # Ver cuántas piezas enemigas mayores o iguales están atacadas desde la nueva casilla
    atacadas = []
    ataques_nueva_casilla = b_next.attacks(move.to_square)
    for sq in ataques_nueva_casilla:
        p_enemiga = b_next.piece_at(sq)
        if p_enemiga and p_enemiga.color == color_rival and p_enemiga.piece_type != chess.PAWN:
            atacadas.append(p_enemiga.piece_type)

    if len(atacadas) >= 2:
        n1 = NOMBRES_PIEZAS.get(atacadas[0], "pieza")
        n2 = NOMBRES_PIEZAS.get(atacadas[1], "pieza")
        if n1 != n2:
            return f"Ataque doble (tenedor) a {n1} y {n2}"
        return f"Ataque doble a piezas rivales desde {to_sq_name}"

    # 7. Clavadas tácticas (si alguna pieza enemiga queda clavada contra el Rey)
    for sq in chess.SQUARES:
        p = b_next.piece_at(sq)
        if p and p.color == color_rival:
            if b_next.is_pinned(color_rival, sq) and not board.is_pinned(color_rival, sq):
                nom_clavada = NOMBRES_PIEZAS.get(p.piece_type, "pieza")
                return f"Clava el {nom_clavada} rival contra el rey"

    # 8. Conceptos Posicionales
    # Columna abierta para Torre o Dama
    if tipo_pieza in (chess.ROOK, chess.QUEEN):
        file_idx = chess.square_file(move.to_square)
        peones_en_col = any(
            b_next.piece_at(chess.square(file_idx, rank)) is not None and 
            b_next.piece_at(chess.square(file_idx, rank)).piece_type == chess.PAWN
            for rank in range(8)
        )
        if not peones_en_col:
            file_letra = chr(ord('a') + file_idx).upper()
            return f"Ocupa y domina la columna abierta {file_letra}"

    # Invasión de 7ª fila
    if tipo_pieza == chess.ROOK:
        rank = chess.square_rank(move.to_square)
        if (color == chess.WHITE and rank == 6) or (color == chess.BLACK and rank == 1):
            return f"Invade la 7ª fila presionando los peones rivales"

    # Puesto avanzado de Caballo (casilla central d4, e4, d5, e5, c5, f5 defendida por peón)
    if tipo_pieza == chess.KNIGHT:
        rank = chess.square_rank(move.to_square)
        file_idx = chess.square_file(move.to_square)
        if 2 <= rank <= 5 and 2 <= file_idx <= 5:
            # Comprobar si está defendido por un peón propio
            defensores_peon = [
                sq for sq in b_next.attackers(color, move.to_square) 
                if b_next.piece_at(sq).piece_type == chess.PAWN
            ]
            if defensores_peon:
                return f"Instala el caballo en un puesto avanzado en {to_sq_name}"

    # Ocupación central en apertura
    if tipo_pieza == chess.PAWN and move.to_square in (chess.E4, chess.D4, chess.E5, chess.D5):
        return f"Controla el centro y activa el desarrollo"

    # Desarrollo de piezas menores
    if tipo_pieza in (chess.KNIGHT, chess.BISHOP):
        rank_orig = chess.square_rank(move.from_square)
        if (color == chess.WHITE and rank_orig == 0) or (color == chess.BLACK and rank_orig == 7):
            return f"Desarrolla {nombre_pieza} hacia el centro"

    # Defensa de una pieza amenazada
    defensores_previos = board.attackers(color, move.to_square)
    if board.is_attacked_by(color_rival, move.to_square) and defensores_previos:
        return f"Refuerza el control de la casilla clave {to_sq_name}"

    return f"Mejora la posición de {nombre_pieza} en {to_sq_name}"
