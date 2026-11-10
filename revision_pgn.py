from dataclasses import dataclass, replace
from pathlib import Path

import chess
import chess.engine
import chess.pgn


@dataclass(frozen=True)
class ErrorRevision:
    tablero: chess.Board
    jugada: chess.Move
    variante: tuple[chess.Move, ...]
    perdida: int
    cambio_mate: bool = False
    alternativas: tuple[tuple[chess.Move, ...], ...] = ()


def cargar_partida(ruta):
    archivo = Path(ruta)
    try:
        with archivo.open(encoding='utf-8-sig') as entrada:
            partida = chess.pgn.read_game(entrada)
    except UnicodeDecodeError:
        with archivo.open(encoding='latin-1') as entrada:
            partida = chess.pgn.read_game(entrada)

    if partida is None or partida.errors or not partida.variations:
        raise ValueError('El PGN no contiene una primera partida válida con jugadas.')
    tablero = partida.board()
    if type(tablero) is not chess.Board or tablero.chess960 or not tablero.is_valid():
        raise ValueError('El PGN debe empezar en una posición válida de ajedrez estándar.')
    return partida


def revisar_partida(partida, bando, motor, *, tiempo=0.12, progreso=None, cancelado=None):
    tablero = partida.board()
    jugadas = list(partida.mainline_moves())
    total = (len(jugadas) + int(tablero.turn == bando)) // 2
    hechos = 0
    errores = []
    limite = chess.engine.Limit(time=tiempo)

    for jugada in jugadas:
        if cancelado and cancelado():
            return []
        if tablero.turn == bando:
            mejor = motor.analyse(tablero, limite)
            variante = mejor['pv']
            if variante and variante[0] != jugada:
                if cancelado and cancelado():
                    return []
                jugada_real = motor.analyse(tablero, limite, root_moves=[jugada])
                score_mejor = mejor['score'].pov(bando)
                score_real = jugada_real['score'].pov(bando)
                perdida = score_mejor.score(mate_score=10000) - score_real.score(mate_score=10000)
                if perdida >= 50:
                    cambio_mate = score_mejor.is_mate() or score_real.is_mate()
                    errores.append(ErrorRevision(tablero.copy(stack=False), jugada, tuple(variante[:5]), perdida, cambio_mate))
            hechos += 1
            if progreso:
                progreso(hechos, total)
        tablero.push(jugada)

    return sorted(errores, key=lambda error: error.perdida, reverse=True)[:3]


def _lineas_evaluadas(tablero, motor, *, multipv, tiempo, root_moves=None):
    resultados = motor.analyse(tablero, chess.engine.Limit(time=tiempo), multipv=multipv, root_moves=root_moves)
    return [
        (tuple(info['pv'][:5]), info['score'].pov(tablero.turn))
        for info in resultados if info.get('pv') and info.get('score') is not None
    ]


def _evaluacion_cercana(mejor, candidata):
    if mejor.is_mate() or candidata.is_mate():
        return (
            mejor.is_mate() and candidata.is_mate()
            and mejor.score(mate_score=10000) - candidata.score(mate_score=10000) <= 1
        )
    return mejor.score() - candidata.score() <= 25


def preparar_alternativas(error, motor, *, tiempo=0.35):
    lineas = _lineas_evaluadas(error.tablero, motor, multipv=5, tiempo=tiempo)
    if not lineas:
        return error
    mejor_score = max(score for _, score in lineas)
    alternativas = tuple(
        variante for variante, score in lineas
        if variante[0] != error.variante[0] and _evaluacion_cercana(mejor_score, score)
    )
    return replace(error, alternativas=alternativas)


def evaluar_alternativa(error, intento, motor, *, tiempo=0.5):
    principal = error.variante[0]
    lineas = _lineas_evaluadas(error.tablero, motor, multipv=2, tiempo=tiempo, root_moves=[principal, intento])
    evaluadas = {variante[0]: (variante, score) for variante, score in lineas}
    if principal not in evaluadas or intento not in evaluadas:
        raise chess.engine.EngineError('Stockfish no devolvió las dos líneas para comparar.')
    variante, score = evaluadas[intento]
    mejor_score = max(evaluadas[principal][1], score)
    return variante if _evaluacion_cercana(mejor_score, score) else ()


class SesionRevision:
    def __init__(self, errores):
        self.errores = errores
        self.seleccionar(0)

    @property
    def error(self):
        return self.errores[self.indice]

    @property
    def tablero(self):
        tablero = self.error.tablero.copy(stack=False)
        for jugada in self.variante[:self.paso]:
            tablero.push(jugada)
        return tablero

    def seleccionar(self, indice):
        self.indice = indice
        self.variante = self.error.variante
        self.paso = 0
        self.en_practica = False
        self.solucion_visible = True

    def avanzar(self, pasos):
        if self.solucion_visible:
            self.paso = max(0, min(self.paso + pasos, len(self.variante)))

    def practicar(self):
        self.variante = self.error.variante
        self.paso = 0
        self.en_practica = True
        self.solucion_visible = False

    def revelar(self):
        self.solucion_visible = True

    def aceptar_alternativa(self, variante):
        self.variante = variante
        self.revelar()

    def intentar(self, origen, destino):
        tablero = self.error.tablero
        solucion = self.error.variante[0]
        # Una flecha indica origen y destino. La variante muestra la pieza de coronación.
        if (origen, destino) == (solucion.from_square, solucion.to_square):
            self.revelar()
            return 'correcta'
        for variante in self.error.alternativas:
            jugada = variante[0]
            if (origen, destino) == (jugada.from_square, jugada.to_square):
                self.aceptar_alternativa(variante)
                return 'buena_alternativa'
        if any(jugada.to_square == destino for jugada in tablero.generate_legal_moves(from_mask=chess.BB_SQUARES[origen])):
            return 'alternativa'
        return 'ilegal'
