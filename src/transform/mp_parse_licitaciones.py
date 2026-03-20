from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def load_latest_raw(prefix: str = "mp_raw_") -> Dict[str, Any]:
    files = sorted(RAW_DIR.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No hay archivos {prefix}*.json en {RAW_DIR}")
    latest = files[0]
    with latest.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_get(d: Dict[str, Any], *keys: str, default=None):
    cur: Any = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def parse_licitaciones(payload: Dict[str, Any]) -> pd.DataFrame:
    """
    Nota: la estructura exacta del JSON puede variar.
    Este parser intenta encontrar una lista de 'Listado' o similar.
    Si el nombre difiere, lo ajustamos según tu JSON real.
    """
    # Intentos comunes:
    items = safe_get(payload, "Listado", default=None) or safe_get(payload, "ListadoLicitaciones", default=None)

    if items is None:
        # Si no encontramos, guardamos llaves para inspección rápida
        raise KeyError(f"No se encontró 'Listado' en el JSON. Keys disponibles: {list(payload.keys())}")

    rows: List[Dict[str, Any]] = []
    for it in items:
        rows.append({
            "codigo_licitacion": safe_get(it, "CodigoExterno"),
            "nombre_licitacion": safe_get(it, "Nombre"),
            "estado": safe_get(it, "CodigoEstado"),
            "fecha_publicacion": safe_get(it, "FechaPublicacion"),
            "fecha_cierre": safe_get(it, "FechaCierre"),
            "comprador_nombre": safe_get(it, "Comprador", "NombreOrganismo"),
            "comprador_rut": safe_get(it, "Comprador", "RutUnidad"),
            "region": safe_get(it, "Comprador", "RegionUnidad"),
        })

    df = pd.DataFrame(rows)

    # Limpieza mínima
    for col in ["fecha_publicacion", "fecha_cierre"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def save_processed(df: pd.DataFrame) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = PROCESSED_DIR / f"licitaciones_processed_{ts}.csv"
    df.to_csv(out, index=False, encoding="utf-8")
    return out


def main():
    payload = load_latest_raw()
    df = parse_licitaciones(payload)
    out = save_processed(df)
    print(f"[OK] Procesado guardado en: {out}")
    print(df.head(10))


if __name__ == "__main__":
    main()