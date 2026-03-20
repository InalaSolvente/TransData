from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

BASE_URL = "https://api.mercadopublico.cl/servicios/v1"


def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("MP_API_KEY")
    if not key:
        raise RuntimeError("Falta MP_API_KEY en tu .env")
    return key


def load_latest_raw_list() -> Dict[str, Any]:
    files = sorted(RAW_DIR.glob("mp_raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError("No hay mp_raw_*.json en data/raw")
    latest = files[0]
    with latest.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_get(d: Any, *keys: str, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def fetch_detail(codigo_externo: str, api_key: str, timeout: int = 30, retries: int = 5) -> Dict[str, Any]:
    url = f"{BASE_URL}/publico/licitaciones.json"
    params = {"ticket": api_key, "codigo": codigo_externo}

    last_err: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, params=params, timeout=timeout)

            # Si el servidor cae (500), reintenta con backoff
            if r.status_code >= 500:
                wait = 0.8 * attempt  # backoff simple
                print(f"[WARN] {codigo_externo} -> {r.status_code} (server). Reintento {attempt}/{retries} en {wait:.1f}s")
                time.sleep(wait)
                continue

            r.raise_for_status()
            return r.json()

        except Exception as e:
            last_err = e
            wait = 0.8 * attempt
            print(f"[WARN] {codigo_externo} -> error en intento {attempt}/{retries}. Reintento en {wait:.1f}s. Error: {type(e).__name__}")
            time.sleep(wait)

    raise RuntimeError(f"Detalle falló para {codigo_externo}. Último error: {last_err}")


def parse_detail(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    La respuesta de detalle suele venir con una estructura anidada.
    Esta función intenta extraer campos comunes y deja None si no existen.
    Ajustamos si tu JSON de detalle usa otros nombres.
    """
    # A veces el detalle viene en: "Listado"[0] o "Licitacion" o "Items"
    lic = None
    if isinstance(payload.get("Listado"), list) and payload["Listado"]:
        lic = payload["Listado"][0]
    else:
        # fallback: intenta otras keys
        lic = payload.get("Licitacion") or payload

    return {
        "codigo_licitacion": safe_get(lic, "CodigoExterno"),
        "nombre_licitacion": safe_get(lic, "Nombre"),
        "estado": safe_get(lic, "CodigoEstado"),
        "fecha_publicacion": safe_get(lic, "Fechas", "FechaPublicacion"),
        "fecha_cierre": safe_get(lic, "Fechas", "FechaCierre") or safe_get(lic, "FechaCierre"),
        "comprador_nombre": safe_get(lic, "Comprador", "NombreOrganismo") or safe_get(lic, "Comprador", "Nombre"),
        "comprador_rut": safe_get(lic, "Comprador", "RutUnidad") or safe_get(lic, "Comprador", "RutOrganismo"),
        "region": safe_get(lic, "Comprador", "RegionUnidad") or safe_get(lic, "Comprador", "Region"),
    }


def main():
    api_key = load_api_key()
    raw = load_latest_raw_list()
    listado = raw.get("Listado", [])

    if not listado:
        raise RuntimeError("El JSON raw no trae Listado o viene vacío.")

    codigos = [x.get("CodigoExterno") for x in listado if x.get("CodigoExterno")]
    print(f"[INFO] Códigos encontrados: {len(codigos)}")

    rows: List[Dict[str, Any]] = []
    errors = 0

    # Rate limit: pausa entre requests para no ser bloqueado
    SLEEP_SEC = 0.35  # ajustable

    for i, code in enumerate(codigos, start=1):
        try:
            detail = fetch_detail(code, api_key)
            row = parse_detail(detail)
            rows.append(row)
        except Exception as e:
            errors += 1
            rows.append({
                "codigo_licitacion": code,
                "nombre_licitacion": None,
                "estado": None,
                "fecha_publicacion": None,
                "fecha_cierre": None,
                "comprador_nombre": None,
                "comprador_rut": None,
                "region": None,
                "error": f"{type(e).__name__}: {getattr(e, 'args', [''])[0]}",
            })
            print(f"[WARN] Error en {code}: {e}")

        if i % 25 == 0:
            print(f"[INFO] procesadas {i}/{len(codigos)} (errores: {errors})")

        time.sleep(SLEEP_SEC)

    df = pd.DataFrame(rows)

    # Limpieza fechas
    for col in ["fecha_publicacion", "fecha_cierre"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = PROCESSED_DIR / f"licitaciones_enriched_{ts}.csv"
    df.to_csv(out, index=False, encoding="utf-8")

    print(f"[OK] CSV enriquecido guardado en: {out}")
    print(df.head(10))


if __name__ == "__main__":
    main()
