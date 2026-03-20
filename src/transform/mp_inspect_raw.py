import json
from pathlib import Path

RAW_DIR = Path("data/raw")

def load_latest_raw():
    files = sorted(RAW_DIR.glob("mp_raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No hay mp_raw_*.json en data/raw")
    latest = files[0]
    with latest.open("r", encoding="utf-8") as f:
        return json.load(f), latest

def main():
    payload, path = load_latest_raw()
    print("Archivo raw:", path)
    print("Keys raíz:", list(payload.keys()))

    listado = payload.get("Listado", [])
    print("Cantidad Listado:", len(listado))
    if not listado:
        return

    item = listado[0]
    print("\nKeys del primer item:")
    print(list(item.keys()))

    # imprime algunas claves y valores visibles sin explotar la pantalla
    print("\nPrimer item (preview):")
    for k in list(item.keys())[:25]:
        v = item.get(k)
        if isinstance(v, (dict, list)):
            print(f"- {k}: ({type(v).__name__})")
        else:
            print(f"- {k}: {v}")

    # si hay dicts comunes, los mostramos
    for candidate in ["Comprador", "Organismo", "Unidad", "Buyer", "Entidad", "Institucion"]:
        if candidate in item:
            print(f"\nDetalle {candidate}:")
            print(item[candidate])

if __name__ == "__main__":
    main()