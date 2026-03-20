from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

RAW_DIR = Path("data/raw")


def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("MP_API_KEY")
    if not key:
        raise RuntimeError("Falta MP_API_KEY en el archivo .env (en la raíz del proyecto).")
    return key


def fetch_json(url: str, params: Dict[str, Any], timeout: int = 30, retries: int = 3) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_err = e
            print(f"[WARN] intento {attempt}/{retries} falló: {e}")
    raise RuntimeError(f"No se pudo obtener respuesta JSON. Último error: {last_err}")


def save_raw(payload: Dict[str, Any]) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RAW_DIR / f"mp_raw_{ts}.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return out


def main() -> None:
    api_key = load_api_key()

    # Endpoint base (ajusta si tu documentación dice otra versión/ruta)
    url = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"

    # Parámetros mínimos (cambia 'ticket' a 'apikey' si tu doc lo indica)
    params = {
        "ticket": api_key,
        "estado": "publicada",
        "pagina": 1,
    }

    payload = fetch_json(url, params=params)
    out = save_raw(payload)
    print(f"[OK] Guardado JSON crudo en: {out}")


if __name__ == "__main__":
    main()
