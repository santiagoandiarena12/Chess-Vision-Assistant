import os
import json
import zipfile
import io
import urllib.request
from pathlib import PurePosixPath

AVISOS_STOCKFISH = {"authors", "citation.cff", "copying.txt", "readme.md", "top cpu contributors.txt"}

def descargar():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    stockfish_dir = os.path.join(base_dir, "stockfish")
    os.makedirs(stockfish_dir, exist_ok=True)

    print("Conectando con el repositorio oficial de Stockfish...")
    req = urllib.request.Request(
        "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        
    paquetes_windows = [
        paquete for paquete in data.get("assets", [])
        if "windows-x86-64" in paquete["name"].lower() and paquete["name"].lower().endswith(".zip")
    ]
    asset = next((paquete for paquete in paquetes_windows if "universal" in paquete["name"].lower()), None)
    if asset is None and paquetes_windows:
        asset = paquetes_windows[0]

    if not asset:
        print("[!] No se encontró el asset de Windows.")
        return None

    nombre_archivo = asset["name"]
    url = asset["browser_download_url"]
    print(f"Descargando {nombre_archivo}...")

    req_file = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_file) as resp:
        zip_bytes = resp.read()

    print("Instalando el motor de Stockfish...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as paquete:
        archivos = [PurePosixPath(entrada.filename) for entrada in paquete.infolist() if not entrada.is_dir()]
        ejecutable = next((archivo for archivo in archivos if archivo.suffix.lower() == ".exe"), None)
        if ejecutable is None:
            print("[!] El paquete de Stockfish no contiene un ejecutable .exe.")
            return None

        for archivo in archivos:
            if archivo.parent == ejecutable.parent and archivo.name.lower() in AVISOS_STOCKFISH:
                paquete.extract(archivo.as_posix(), stockfish_dir)
        exe_encontrado = paquete.extract(ejecutable.as_posix(), stockfish_dir)

    print(f"[OK] Stockfish instalado con éxito en:\n     {exe_encontrado}")
    with open(os.path.join(base_dir, "stockfish_path.txt"), "w", encoding="utf-8") as f:
        f.write(os.path.relpath(exe_encontrado, base_dir))
    return exe_encontrado

if __name__ == "__main__":
    descargar()
