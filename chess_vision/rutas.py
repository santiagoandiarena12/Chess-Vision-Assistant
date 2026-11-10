from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
DATOS_LOCALES = RAIZ_PROYECTO / "datos_locales"
RECURSOS = RAIZ_PROYECTO / "recursos"

PLANTILLAS_PIEZAS = RECURSOS / "piezas"
PIEZAS_HD = RECURSOS / "piezas_hd"
COORDENADAS = DATOS_LOCALES / "coordenadas.json"
STOCKFISH_CONFIG = DATOS_LOCALES / "stockfish_path.txt"


def ruta_local(actual: Path) -> Path:
    """Permite leer recursos de instalaciones previas en la raíz del proyecto."""
    anterior = RAIZ_PROYECTO / actual.name
    return anterior if not actual.exists() and anterior.exists() else actual
