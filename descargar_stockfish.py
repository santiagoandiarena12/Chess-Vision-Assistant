import os
import json
import zipfile
import io
import urllib.request

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
        
    asset = None
    for a in data.get("assets", []):
        if "windows-x86-64-universal" in a["name"].lower():
            asset = a
            break
            
    if not asset:
        # Fallback a cualquier versión windows x86-64
        for a in data.get("assets", []):
            if "windows" in a["name"].lower() and "64" in a["name"].lower():
                asset = a
                break

    if not asset:
        print("[!] No se encontró el asset de Windows.")
        return None

    nombre_archivo = asset["name"]
    url = asset["browser_download_url"]
    print(f"Descargando {nombre_archivo} (~40-60 MB)...")

    req_file = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req_file) as resp:
        zip_bytes = resp.read()

    print("Descomprimiendo archivos...")
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        z.extractall(stockfish_dir)

    exe_encontrado = None
    for root, _, files in os.walk(stockfish_dir):
        for f in files:
            if f.lower().endswith(".exe"):
                exe_encontrado = os.path.join(root, f)
                break
        if exe_encontrado:
            break

    if exe_encontrado:
        print(f"[OK] Stockfish instalado con éxito en:\n     {exe_encontrado}")
        # Guardar la ruta en un archivo de configuración
        with open(os.path.join(base_dir, "stockfish_path.txt"), "w", encoding="utf-8") as f:
            f.write(os.path.relpath(exe_encontrado, base_dir))
        return exe_encontrado
    else:
        print("[!] No se encontró el ejecutable .exe tras descomprimir.")
        return None

if __name__ == "__main__":
    descargar()
