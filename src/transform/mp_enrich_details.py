from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = ROOT / "data" / "master"
TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def load_api_key() -> str:
    load_env()
    key = os.getenv("MP_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("Falta MP_API_KEY valido en .env")
    return key


def env_int(name: str, default: Optional[int] = None) -> Optional[int]:
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'")
    if value == "":
        return default
    return int(value)


def env_float(name: str, default: float) -> float:
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'")
    if value == "":
        return default
    return float(value)


def safe_get(data: Any, *keys: str, default=None):
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def truncate_text(value, max_len=500):
    if value is None:
        return None
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "...[truncated]"


def fetch_detail(codigo_externo: str, api_key: str, timeout: int = 45, retries: int = 6) -> Dict[str, Any]:
    params = {"ticket": api_key, "codigo": codigo_externo}
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(BASE_URL, params=params, timeout=timeout)

            if response.status_code >= 500:
                wait = min(30.0, float(attempt * 2))
                print(f"[WARN] {codigo_externo} -> {response.status_code}. Reintento en {wait:.1f}s")
                time.sleep(wait)
                continue

            response.raise_for_status()
            return {
                "ok": True,
                "status_code": response.status_code,
                "payload": response.json(),
                "error": None,
                "response_snippet": None,
            }

        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            wait = min(30.0, float(attempt * 2))
            print(f"[WARN] {codigo_externo} -> {last_error}. Reintento en {wait:.1f}s")
            time.sleep(wait)

    return {
        "ok": False,
        "status_code": None,
        "payload": None,
        "error": last_error,
        "response_snippet": None,
    }


def parse_detail(payload: Dict[str, Any]) -> Dict[str, Any]:
    licitacion = None

    if isinstance(payload.get("Listado"), list) and payload["Listado"]:
        licitacion = payload["Listado"][0]
    else:
        licitacion = payload.get("Licitacion") or payload

    return {
        "detalle_nombre": safe_get(licitacion, "Nombre"),
        "detalle_codigo_estado": safe_get(licitacion, "CodigoEstado"),
        "detalle_estado": safe_get(licitacion, "Estado"),
        "detalle_fecha_publicacion": (
            safe_get(licitacion, "Fechas", "FechaPublicacion")
            or safe_get(licitacion, "FechaCreacion")
        ),
        "detalle_fecha_cierre": (
            safe_get(licitacion, "Fechas", "FechaCierre")
            or safe_get(licitacion, "FechaCierre")
        ),
        "detalle_descripcion": safe_get(licitacion, "Descripcion"),
        "detalle_comprador_nombre": safe_get(licitacion, "Comprador", "NombreOrganismo"),
        "detalle_comprador_rut": (
            safe_get(licitacion, "Comprador", "RutUnidad")
            or safe_get(licitacion, "Comprador", "RutOrganismo")
        ),
        "detalle_comprador_region": safe_get(licitacion, "Comprador", "RegionUnidad"),
        "detalle_comprador_comuna": safe_get(licitacion, "Comprador", "ComunaUnidad"),
        "detalle_unidad_nombre": safe_get(licitacion, "Comprador", "NombreUnidad"),
        "detalle_monto_estimado": safe_get(licitacion, "MontoEstimado"),
        "detalle_moneda": safe_get(licitacion, "Moneda"),
        "detalle_url_ficha": safe_get(licitacion, "UrlFicha"),
        "detalle_items_count": len(safe_get(licitacion, "Items", "Listado", default=[]) or []),
        "detalle_adj_count": len(safe_get(licitacion, "Items", "Adjudicacion", default=[]) or []),
    }


def ensure_enrich_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    columns = [
        "detalle_nombre",
        "detalle_codigo_estado",
        "detalle_estado",
        "detalle_fecha_publicacion",
        "detalle_fecha_cierre",
        "detalle_descripcion",
        "detalle_comprador_nombre",
        "detalle_comprador_rut",
        "detalle_comprador_region",
        "detalle_comprador_comuna",
        "detalle_unidad_nombre",
        "detalle_monto_estimado",
        "detalle_moneda",
        "detalle_url_ficha",
        "detalle_items_count",
        "detalle_adj_count",
        "detalle_http_status",
        "detalle_error",
        "detalle_status",
        "detalle_first_attempt_at",
        "detalle_last_attempt_at",
        "detalle_last_success_at",
        "detalle_last_error_at",
        "detalle_attempts_total",
        "detalle_needs_retry",
        "detalle_enriched_at",
        "enriched",
    ]

    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA

    return df


def coerce_bool_series(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "si", "yes"})


def coerce_int_series(series: pd.Series, default: int = 0) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(default)
    return numeric.astype(int)


def coerce_datetime_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def ensure_update_column_dtype(df_master: pd.DataFrame, column: str, update_series: pd.Series) -> pd.DataFrame:
    if column not in df_master.columns:
        df_master[column] = pd.NA

    if pd.api.types.is_object_dtype(update_series.dtype):
        df_master[column] = df_master[column].astype("object")
    elif pd.api.types.is_bool_dtype(update_series.dtype):
        df_master[column] = df_master[column].astype("object")

    return df_master


def load_transport_master(master_path=TRANSPORT_MASTER_PATH) -> pd.DataFrame:
    if not Path(master_path).exists():
        raise FileNotFoundError(f"No existe transport master: {master_path}")
    return pd.read_csv(master_path, encoding="utf-8-sig")


def get_codes_pending_enrich(
    df: pd.DataFrame,
    limit: Optional[int] = None,
    only_errors: bool = False,
    max_attempts_per_code: Optional[int] = None,
) -> List[str]:
    enriched_series = df.get("enriched", pd.Series([False] * len(df)))
    pending = df[~coerce_bool_series(enriched_series.fillna(False))].copy()

    if only_errors:
        status_series = pending.get("detalle_status", pd.Series(["pending"] * len(pending)))
        pending = pending[status_series.fillna("").astype(str).str.lower() == "error"].copy()

    pending["detalle_status"] = pending.get("detalle_status", pd.Series(["pending"] * len(pending))).fillna("pending").astype(str).str.lower()
    pending["detalle_attempts_total"] = coerce_int_series(
        pending.get("detalle_attempts_total", pd.Series([0] * len(pending)))
    )
    pending["detalle_last_attempt_at"] = coerce_datetime_series(
        pending.get("detalle_last_attempt_at", pd.Series([pd.NaT] * len(pending)))
    )

    if max_attempts_per_code is not None:
        pending = pending[pending["detalle_attempts_total"] < max_attempts_per_code].copy()

    # Priorizamos registros nunca intentados y luego errores antiguos con menos intentos.
    pending["priority_group"] = pending["detalle_status"].map(
        {"pending": 0, "error": 1}
    ).fillna(2)
    pending = pending.sort_values(
        by=["priority_group", "detalle_attempts_total", "detalle_last_attempt_at"],
        ascending=[True, True, True],
        na_position="first",
    )

    codes = (
        pending["codigo_licitacion"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    if limit is not None:
        return codes[:limit]
    return codes


def summarize_enrich_backlog(df: pd.DataFrame) -> Dict[str, Any]:
    df = ensure_enrich_columns(df)
    status_series = df["detalle_status"].fillna("pending").astype(str).str.lower()
    enriched_series = coerce_bool_series(df["enriched"].fillna(False))
    retry_series = coerce_bool_series(df["detalle_needs_retry"].fillna("").astype(str))
    attempts_series = coerce_int_series(df["detalle_attempts_total"].fillna(0))

    return {
        "total_rows": int(len(df)),
        "enriched_rows": int(enriched_series.sum()),
        "pending_rows": int((~enriched_series).sum()),
        "pending_status_rows": int((status_series == "pending").sum()),
        "error_status_rows": int((status_series == "error").sum()),
        "retry_needed_rows": int(retry_series.sum()),
        "average_attempts": float(attempts_series.mean()) if len(attempts_series) else 0.0,
        "max_attempts": int(attempts_series.max()) if len(attempts_series) else 0,
    }


def write_enrich_summary(master_path: Path, summary: Dict[str, Any]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = master_path.parent / f"mp_enrich_transport_summary_{timestamp}.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return summary_path


def enrich_transport_master(
    master_path=TRANSPORT_MASTER_PATH,
    limit: Optional[int] = None,
    sleep_sec: Optional[float] = None,
    only_errors: bool = False,
    max_attempts_per_code: Optional[int] = None,
    pause_every: Optional[int] = None,
    pause_seconds: Optional[float] = None,
):
    master_path = Path(master_path)
    api_key = load_api_key()
    if limit is None:
        limit = env_int("MP_ENRICH_LIMIT", None)
    if sleep_sec is None:
        sleep_sec = env_float("MP_ENRICH_SLEEP_SEC", 0.8)
    if pause_every is None:
        pause_every = env_int("MP_ENRICH_PAUSE_EVERY", 100)
    if pause_seconds is None:
        pause_seconds = env_float("MP_ENRICH_PAUSE_SECONDS", 4.0)

    df_master = ensure_enrich_columns(load_transport_master(master_path))

    if "codigo_licitacion" not in df_master.columns:
        raise RuntimeError("El transport master no contiene codigo_licitacion")

    pending_codes = get_codes_pending_enrich(
        df_master,
        limit=limit,
        only_errors=only_errors,
        max_attempts_per_code=max_attempts_per_code,
    )
    print(f"[INFO] Codigos pendientes de enrich: {len(pending_codes)}")

    rows = []
    errors = 0
    successes = 0

    for index, code in enumerate(pending_codes, start=1):
        print(f"[INFO] Enrich {index}/{len(pending_codes)} -> {code}")

        result = fetch_detail(code, api_key)
        attempted_at = datetime.now().isoformat()
        if result["ok"]:
            successes += 1
            detail = parse_detail(result["payload"])
            row = {
                "codigo_licitacion": code,
                **detail,
                "detalle_http_status": result["status_code"],
                "detalle_error": None,
                "detalle_status": "success",
                "detalle_first_attempt_at": pd.NA,
                "detalle_last_attempt_at": attempted_at,
                "detalle_last_success_at": attempted_at,
                "detalle_last_error_at": pd.NA,
                "detalle_needs_retry": False,
                "detalle_enriched_at": datetime.now().isoformat(),
                "enriched": True,
            }
        else:
            errors += 1
            row = {
                "codigo_licitacion": code,
                "detalle_nombre": pd.NA,
                "detalle_codigo_estado": pd.NA,
                "detalle_estado": pd.NA,
                "detalle_fecha_publicacion": pd.NA,
                "detalle_fecha_cierre": pd.NA,
                "detalle_descripcion": pd.NA,
                "detalle_comprador_nombre": pd.NA,
                "detalle_comprador_rut": pd.NA,
                "detalle_comprador_region": pd.NA,
                "detalle_comprador_comuna": pd.NA,
                "detalle_unidad_nombre": pd.NA,
                "detalle_monto_estimado": pd.NA,
                "detalle_moneda": pd.NA,
                "detalle_url_ficha": pd.NA,
                "detalle_items_count": pd.NA,
                "detalle_adj_count": pd.NA,
                "detalle_http_status": result["status_code"],
                "detalle_error": result["error"],
                "detalle_status": "error",
                "detalle_first_attempt_at": pd.NA,
                "detalle_last_attempt_at": attempted_at,
                "detalle_last_success_at": pd.NA,
                "detalle_last_error_at": attempted_at,
                "detalle_needs_retry": True,
                "detalle_enriched_at": datetime.now().isoformat(),
                "enriched": False,
            }

        rows.append(row)
        time.sleep(sleep_sec)

        if pause_every and pause_every > 0 and index % pause_every == 0 and index < len(pending_codes):
            print(f"[INFO] Pausa corta tras {index} codigos enriquecidos ({pause_seconds:.1f}s)")
            time.sleep(pause_seconds)

    if rows:
        df_updates = pd.DataFrame(rows).set_index("codigo_licitacion")
        df_master = df_master.set_index("codigo_licitacion")

        current_attempts = coerce_int_series(
            df_master.get("detalle_attempts_total", pd.Series([0] * len(df_master), index=df_master.index))
        )
        update_attempts = current_attempts.reindex(df_updates.index, fill_value=0) + 1
        df_updates["detalle_attempts_total"] = update_attempts.values
        existing_first_attempt = df_master.get(
            "detalle_first_attempt_at",
            pd.Series([pd.NA] * len(df_master), index=df_master.index),
        ).reindex(df_updates.index)
        df_updates["detalle_first_attempt_at"] = existing_first_attempt.where(
            existing_first_attempt.notna(),
            df_updates["detalle_last_attempt_at"],
        ).values

        for column in df_updates.columns:
            df_master = ensure_update_column_dtype(df_master, column, df_updates[column])
            df_master.loc[df_updates.index, column] = df_updates[column]

        df_master = df_master.reset_index()

    for column in ["detalle_fecha_publicacion", "detalle_fecha_cierre"]:
        if column in df_master.columns:
            df_master[column] = pd.to_datetime(df_master[column], errors="coerce")

    df_master.to_csv(master_path, index=False, encoding="utf-8-sig")

    backlog_summary = summarize_enrich_backlog(df_master)
    summary = {
        "master_path": str(master_path),
        "pending_codes": len(pending_codes),
        "successes": successes,
        "errors": errors,
        "updated_at": datetime.now().isoformat(),
        **backlog_summary,
        "only_errors": only_errors,
        "max_attempts_per_code": max_attempts_per_code,
        "sleep_sec": sleep_sec,
        "pause_every": pause_every,
        "pause_seconds": pause_seconds,
        "configured_limit": limit,
    }
    summary_path = write_enrich_summary(master_path, summary)
    summary["summary_path"] = str(summary_path)

    print(f"[OK] Transport master enriquecido: {master_path}")
    print(f"[INFO] Codigos procesados: {len(pending_codes)}")
    print(f"[INFO] Exitos: {successes}")
    print(f"[INFO] Errores: {errors}")
    print(f"[INFO] Resumen enrich: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Enriquece licitaciones del transport master.")
    parser.add_argument(
        "--master-path",
        type=Path,
        default=TRANSPORT_MASTER_PATH,
        help="Ruta al transport master.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limita la cantidad de codigos a enriquecer en esta corrida. Si no se indica, usa MP_ENRICH_LIMIT del .env.",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=None,
        help="Pausa entre consultas de detalle. Si no se indica, usa MP_ENRICH_SLEEP_SEC del .env.",
    )
    parser.add_argument(
        "--only-errors",
        action="store_true",
        help="Solo reintenta codigos con estado previo de error.",
    )
    parser.add_argument(
        "--max-attempts-per-code",
        type=int,
        default=None,
        help="Limita reintentos acumulados por codigo.",
    )
    parser.add_argument(
        "--pause-every",
        type=int,
        default=None,
        help="Pausa corta cada N codigos procesados. Si no se indica, usa MP_ENRICH_PAUSE_EVERY del .env.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=None,
        help="Duracion de la pausa corta entre lotes. Si no se indica, usa MP_ENRICH_PAUSE_SECONDS del .env.",
    )
    args = parser.parse_args()

    enrich_transport_master(
        master_path=args.master_path,
        limit=args.limit,
        sleep_sec=args.sleep_sec,
        only_errors=args.only_errors,
        max_attempts_per_code=args.max_attempts_per_code,
        pause_every=args.pause_every,
        pause_seconds=args.pause_seconds,
    )


if __name__ == "__main__":
    main()
