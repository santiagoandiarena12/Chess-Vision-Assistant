import os
import urllib.request

PIEZAS_DIR = os.path.join(os.path.dirname(__file__), "piezas_hd")

PIEZAS = ["wK", "wQ", "wR", "wB", "wN", "wP", "bK", "bQ", "bR", "bB", "bN", "bP"]

def descargar_piezas():
    os.makedirs(PIEZAS_DIR, exist_ok=True)
    print("Descargando set gráfico HD desde chessboardjs...")
    
    headers = {"User-Agent": "Mozilla/5.0"}
    for p in PIEZAS:
        url = f"https://chessboardjs.com/img/chesspieces/wikipedia/{p}.png"
        ruta_destino = os.path.join(PIEZAS_DIR, f"{p}.png")
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(ruta_destino, "wb") as f:
            f.write(resp.read())
        print(f"  [OK] {p}.png")
        
    print("[OK] ¡Todas las 12 piezas HD descargadas con éxito!")

if __name__ == "__main__":
    descargar_piezas()
