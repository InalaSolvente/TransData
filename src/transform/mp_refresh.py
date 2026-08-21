from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
HISTORY_DIR = DATA_DIR / "history"
RAW_REFRESH_DIR = DATA_DIR / "raw" / "refresh"

GENERAL_MASTER_PATH = MASTER_DIR / "licitaciones_master.csv"
TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
TRANSPORT_HISTORY_PATH = HISTORY_DIR / "licitaciones_transport_status_history.csv"

API_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
ESTADOS_TERMINALES = {"7", "8", "18"}


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def env_int(name: str, default: int) -> int:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return int(value) if value else default


def env_float(name: str, default: float) -> float:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return float(value) if value else default


def env_bool(name: str, default: bool) -> bool:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'").lower()
    if value in {"true", "1", "si", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return default


def env_csv_set(name: str, default: set[str]) -> set[str]:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    if not value:
        return set(default)
    return {part.strip().lower() for part in value.split(",") if part.strip()}


def load_api_key() -> str:
    load_env()
    key = os.getenv("MP_API_KEY", "").strip().strip('"').strip("'")
    if not key:
        raise RuntimeError("Falta MP_API_KEY valido en .env")
    return key


def now_str() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_dirs() -> None:
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    RAW_REFRESH_DIR.mkdir(parents=True, exist_ok=True)


def safe_get(data: Any, *keys: str, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def is_missing(value) -> bool:
    if pd.isna(value):
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "nan", "none", "null"}
    return False


def normalize_scalar(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return value


def normalize_status_token(value) -> Optional[str]:
    normalized = normalize_scalar(value)
    if normalized is None:
        return None

    numeric = pd.to_numeric(pd.Series([normalized]), errors="coerce").iloc[0]
    if pd.notna(numeric):
        try:
            return str(int(numeric))
        except Exception:
            pass

    return str(normalized).strip().lower()


def normalize_codigo(value) -> Optional[str]:
    normalized = normalize_scalar(value)
    if normalized is None:
        return None
    code = str(normalized).strip()
    if not code or code.lower() == "nan":
        return None
    return code


def coerce_bool(value, default: bool = False) -> bool:
    if pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "si", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    return default


def ensure_update_column_dtype(df_master: pd.DataFrame, column: str, value) -> pd.DataFrame:
    if column not in df_master.columns:
        df_master[column] = pd.NA

    if pd.isna(value):
        return df_master

    if isinstance(value, str):
        df_master[column] = df_master[column].astype("object")
        return df_master

    if isinstance(value, bool):
        df_master[column] = df_master[column].astype("object")
        return df_master

    return df_master


def load_master(master_path: Path) -> pd.DataFrame:
    if not master_path.exists():
        raise FileNotFoundError(f"No existe master para refresh: {master_path}")
    return pd.read_csv(master_path, encoding="utf-8-sig")


def save_master(df: pd.DataFrame, master_path: Path) -> None:
    df.to_csv(master_path, index=False, encoding="utf-8-sig")


def load_history(history_path: Path) -> pd.DataFrame:
    if history_path.exists():
        return pd.read_csv(history_path, encoding="utf-8-sig")

    return pd.DataFrame(
        columns=[
            "fecha_refresh",
            "codigo_licitacion",
            "estado_anterior",
            "estado_nuevo",
            "cambio_estado",
            "cambio_adjudicacion",
            "adjudicacion_capturada",
            "proveedor_adjudicado_nombre",
            "proveedor_adjudicado_rut",
            "raw_refresh_file",
            "refresh_error",
            "observacion",
        ]
    )


def save_history(df: pd.DataFrame, history_path: Path) -> None:
    df.to_csv(history_path, index=False, encoding="utf-8-sig")


def ensure_master_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    expected = [
        "codigo_licitacion",
        "nombre_licitacion",
        "descripcion",
        "estado_actual",
        "fecha_publicacion",
        "fecha_cierre",
        "dias_publicacion",
        "moneda",
        "monto_estimado",
        "comprador_nombre",
        "comprador_rut",
        "comprador_region",
        "comprador_comuna",
        "unidad_nombre",
        "region",
        "tipo",
        "etapas",
        "url_acta",
        "url_ficha",
        "ultima_revision",
        "ultima_actualizacion_detectada",
        "activo_refresh",
        "proveedor_adjudicado_nombre",
        "proveedor_adjudicado_rut",
        "proveedor_adjudicado_id",
        "fecha_adjudicacion",
        "monto_adjudicado",
        "n_adjudicatarios",
        "adjudicacion_capturada",
        "fecha_captura_adjudicacion",
        "requiere_refresh_adjudicacion",
        "raw_refresh_file",
        "refresh_error",
        "refresh_intentos",
        "refresh_status",
    ]

    for column in expected:
        if column not in df.columns:
            df[column] = pd.NA

    if "codigo_licitacion" in df.columns:
        df["codigo_licitacion"] = df["codigo_licitacion"].astype(str).str.strip()

    return df


def repair_inconsistent_award_flags(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    df = df.copy()
    required_columns = [
        "adjudicacion_capturada",
        "proveedor_adjudicado_nombre",
        "proveedor_adjudicado_rut",
        "proveedor_adjudicado_id",
        "requiere_refresh_adjudicacion",
        "fecha_captura_adjudicacion",
    ]
    for column in required_columns:
        if column not in df.columns:
            df[column] = pd.NA

    captured_mask = df["adjudicacion_capturada"].fillna(False).astype(str).str.lower().isin({"true", "1", "si", "yes"})
    supplier_name = df["proveedor_adjudicado_nombre"].fillna("").astype(str).str.strip()
    supplier_rut = df["proveedor_adjudicado_rut"].fillna("").astype(str).str.strip()
    supplier_id = df["proveedor_adjudicado_id"].fillna("").astype(str).str.strip()

    missing_supplier_mask = supplier_name.eq("") & supplier_rut.eq("") & supplier_id.eq("")
    inconsistent_mask = captured_mask & missing_supplier_mask
    count = int(inconsistent_mask.sum())

    if count:
        df.loc[inconsistent_mask, "adjudicacion_capturada"] = False
        df.loc[inconsistent_mask, "requiere_refresh_adjudicacion"] = True
        df.loc[inconsistent_mask, "fecha_captura_adjudicacion"] = pd.NA

    return df, count


def request_licitacion_by_codigo(
    codigo: str,
    api_key: str,
    timeout: int,
    retries: int,
    retry_backoff_seconds: float,
) -> Dict[str, Any]:
    params = {"codigo": codigo, "ticket": api_key}
    last_error: Optional[str] = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=timeout)

            if response.status_code >= 500 or response.status_code == 429:
                last_error = f"HTTP {response.status_code}"
                if attempt < retries:
                    wait = min(30.0, retry_backoff_seconds * attempt)
                    print(f"[WARN] {codigo} -> {last_error}. Reintento en {wait:.1f}s")
                    time.sleep(wait)
                    continue

            response.raise_for_status()
            return {
                "ok": True,
                "attempts": attempt,
                "status_code": response.status_code,
                "payload": response.json(),
                "error": None,
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < retries:
                wait = min(30.0, retry_backoff_seconds * attempt)
                print(f"[WARN] {codigo} -> {last_error}. Reintento en {wait:.1f}s")
                time.sleep(wait)

    return {
        "ok": False,
        "attempts": retries,
        "status_code": None,
        "payload": None,
        "error": last_error,
    }


def extract_first_licitacion(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    listado = payload.get("Listado")
    if isinstance(listado, list) and listado and isinstance(listado[0], dict):
        return listado[0]

    licitacion = payload.get("Licitacion")
    if isinstance(licitacion, dict):
        return licitacion

    return None


def normalize_detalle_licitacion(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "codigo_licitacion": item.get("CodigoExterno") or item.get("codigo_licitacion"),
        "nombre_licitacion": item.get("Nombre") or item.get("nombre_licitacion"),
        "descripcion": item.get("Descripcion") or item.get("descripcion"),
        "estado_actual": item.get("CodigoEstado") or item.get("Estado") or item.get("estado"),
        "fecha_publicacion": safe_get(item, "Fechas", "FechaPublicacion") or item.get("FechaCreacion"),
        "fecha_cierre": safe_get(item, "Fechas", "FechaCierre") or item.get("FechaCierre"),
        "dias_publicacion": item.get("DiasCierreLicitacion") or item.get("dias_publicacion"),
        "moneda": item.get("Moneda") or item.get("moneda"),
        "monto_estimado": item.get("MontoEstimado") or item.get("monto_estimado"),
        "comprador_nombre": safe_get(item, "Comprador", "NombreOrganismo"),
        "comprador_rut": safe_get(item, "Comprador", "RutUnidad") or safe_get(item, "Comprador", "RutOrganismo"),
        "comprador_region": safe_get(item, "Comprador", "RegionUnidad"),
        "comprador_comuna": safe_get(item, "Comprador", "ComunaUnidad"),
        "unidad_nombre": safe_get(item, "Comprador", "NombreUnidad"),
        "region": safe_get(item, "Comprador", "RegionUnidad"),
        "tipo": item.get("Tipo") or item.get("tipo"),
        "etapas": item.get("Etapas") or item.get("etapas"),
        "url_acta": item.get("UrlActa") or item.get("url_acta"),
        "url_ficha": item.get("UrlFicha") or item.get("url_ficha"),
    }


def build_empty_award() -> Dict[str, Any]:
    return {
        "proveedor_adjudicado_nombre": None,
        "proveedor_adjudicado_rut": None,
        "proveedor_adjudicado_id": None,
        "fecha_adjudicacion": None,
        "monto_adjudicado": None,
        "n_adjudicatarios": None,
    }


def merge_award_dicts(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    merged = {}
    for key in build_empty_award().keys():
        primary_value = normalize_scalar(primary.get(key))
        fallback_value = normalize_scalar(fallback.get(key))
        merged[key] = primary_value if primary_value is not None else fallback_value
    return merged


def extract_award_from_items(licitacion: Dict[str, Any]) -> Dict[str, Any]:
    items_list = safe_get(licitacion, "Items", "Listado", default=[]) or []
    if not isinstance(items_list, list):
        return build_empty_award()

    suppliers = []
    total_amount = 0.0
    has_amount = False

    for item in items_list:
        if not isinstance(item, dict):
            continue
        adjudicacion = item.get("Adjudicacion")
        if not isinstance(adjudicacion, dict):
            continue

        supplier_record = {
            "proveedor_adjudicado_nombre": adjudicacion.get("NombreProveedor") or adjudicacion.get("Proveedor"),
            "proveedor_adjudicado_rut": adjudicacion.get("RutProveedor"),
            "proveedor_adjudicado_id": adjudicacion.get("IdProveedor") or adjudicacion.get("CodigoProveedor"),
            "fecha_adjudicacion": None,
            "monto_adjudicado": None,
            "n_adjudicatarios": None,
        }
        suppliers.append(supplier_record)

        amount = adjudicacion.get("MontoUnitario") or adjudicacion.get("MontoAdjudicado") or adjudicacion.get("Monto")
        amount_num = pd.to_numeric(amount, errors="coerce")
        if pd.notna(amount_num):
            total_amount += float(amount_num)
            has_amount = True

    if not suppliers:
        return build_empty_award()

    first = suppliers[0]
    supplier_names = [normalize_scalar(s.get("proveedor_adjudicado_nombre")) for s in suppliers]
    supplier_names = [name for name in supplier_names if name is not None]

    return {
        "proveedor_adjudicado_nombre": first.get("proveedor_adjudicado_nombre"),
        "proveedor_adjudicado_rut": first.get("proveedor_adjudicado_rut"),
        "proveedor_adjudicado_id": first.get("proveedor_adjudicado_id"),
        "fecha_adjudicacion": None,
        "monto_adjudicado": total_amount if has_amount else None,
        "n_adjudicatarios": len(set(supplier_names)) if supplier_names else len(suppliers),
    }


def extract_award_from_top_level(licitacion: Dict[str, Any]) -> Dict[str, Any]:
    adjudicacion = licitacion.get("Adjudicacion")
    if not isinstance(adjudicacion, dict):
        return build_empty_award()

    return {
        "proveedor_adjudicado_nombre": adjudicacion.get("NombreProveedor") or adjudicacion.get("Proveedor"),
        "proveedor_adjudicado_rut": adjudicacion.get("RutProveedor"),
        "proveedor_adjudicado_id": adjudicacion.get("IdProveedor") or adjudicacion.get("CodigoProveedor"),
        "fecha_adjudicacion": adjudicacion.get("Fecha") or adjudicacion.get("FechaAdjudicacion"),
        "monto_adjudicado": adjudicacion.get("Monto") or adjudicacion.get("MontoAdjudicado"),
        "n_adjudicatarios": adjudicacion.get("NumeroOferentes") or adjudicacion.get("Cantidad"),
    }


def extract_adjudicacion(payload: Dict[str, Any]) -> Dict[str, Any]:
    licitacion = extract_first_licitacion(payload) or {}
    items_award = extract_award_from_items(licitacion)
    top_level_award = extract_award_from_top_level(licitacion)
    merged_award = merge_award_dicts(items_award, top_level_award)

    if normalize_scalar(merged_award.get("fecha_adjudicacion")) is None:
        merged_award["fecha_adjudicacion"] = (
            safe_get(licitacion, "Fechas", "FechaAdjudicacion")
            or safe_get(licitacion, "Fechas", "FechaEstimadaAdjudicacion")
        )

    return merged_award


def should_refresh_row(
    row: pd.Series,
    force_terminal_awards: bool,
    revisit_after_days: int,
    revisit_statuses: set[str],
) -> bool:
    if not coerce_bool(row.get("activo_refresh"), default=True):
        estado_actual = normalize_status_token(row.get("estado_actual"))
        ultima_revision = pd.to_datetime(pd.Series([row.get("ultima_revision")]), errors="coerce").iloc[0]
        stale_enough = pd.notna(ultima_revision) and ultima_revision <= (pd.Timestamp.now() - pd.Timedelta(days=revisit_after_days))
        if not (stale_enough and estado_actual in revisit_statuses):
            return False

    estado_actual = normalize_status_token(row.get("estado_actual"))
    requiere_refresh_adjudicacion = coerce_bool(row.get("requiere_refresh_adjudicacion"), default=True)
    adjudicacion_capturada = coerce_bool(row.get("adjudicacion_capturada"), default=False)
    ultima_revision = pd.to_datetime(pd.Series([row.get("ultima_revision")]), errors="coerce").iloc[0]
    stale_enough = pd.notna(ultima_revision) and ultima_revision <= (pd.Timestamp.now() - pd.Timedelta(days=revisit_after_days))

    if estado_actual is None:
        return True

    if estado_actual not in ESTADOS_TERMINALES:
        return True

    if force_terminal_awards and requiere_refresh_adjudicacion and not adjudicacion_capturada:
        return True

    if stale_enough and estado_actual in revisit_statuses:
        return True

    return False


def select_rows_to_refresh(
    df: pd.DataFrame,
    limit: int,
    force_terminal_awards: bool,
    revisit_after_days: int,
    revisit_statuses: set[str],
    only_never_refreshed: bool = False,
) -> pd.DataFrame:
    mask = df.apply(
        lambda row: should_refresh_row(
            row,
            force_terminal_awards,
            revisit_after_days,
            revisit_statuses,
        ),
        axis=1,
    )
    selected = df[mask].copy()

    # Cola incremental:
    # 1) nunca refrescadas
    # 2) refrescadas con error
    # 3) refrescadas con exito pero aun pendientes
    # Dentro de cada grupo, primero las menos recientes.
    refresh_status = (
        selected.get("refresh_status", pd.Series([pd.NA] * len(selected), index=selected.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    if only_never_refreshed:
        selected = selected[refresh_status.eq("")].copy()
        refresh_status = (
            selected.get("refresh_status", pd.Series([pd.NA] * len(selected), index=selected.index))
            .fillna("")
            .astype(str)
            .str.strip()
            .str.lower()
        )

    ultima_revision_dt = pd.to_datetime(
        selected.get("ultima_revision", pd.Series([pd.NaT] * len(selected), index=selected.index)),
        errors="coerce",
    )

    selected["_refresh_status"] = refresh_status
    selected["_ultima_revision_dt"] = ultima_revision_dt
    selected["_refresh_priority"] = 3
    selected.loc[selected["_refresh_status"].eq(""), "_refresh_priority"] = 0
    selected.loc[selected["_refresh_status"].eq("error"), "_refresh_priority"] = 1
    selected.loc[selected["_refresh_status"].eq("success"), "_refresh_priority"] = 2

    current_status_tokens = selected.get("estado_actual", pd.Series([pd.NA] * len(selected), index=selected.index)).apply(normalize_status_token)
    stale_threshold = pd.Timestamp.now() - pd.Timedelta(days=revisit_after_days)
    stale_revisit_mask = (
        selected["_refresh_status"].eq("success")
        & selected["_ultima_revision_dt"].notna()
        & selected["_ultima_revision_dt"].le(stale_threshold)
        & current_status_tokens.isin(revisit_statuses)
    )
    selected.loc[stale_revisit_mask, "_refresh_priority"] = 1

    selected = selected.sort_values(
        by=["_refresh_priority", "_ultima_revision_dt", "codigo_licitacion"],
        ascending=[True, True, True],
        na_position="first",
    )
    selected = selected.drop(
        columns=["_refresh_status", "_ultima_revision_dt", "_refresh_priority"],
        errors="ignore",
    )

    if limit and len(selected) > limit:
        selected = selected.head(limit).copy()

    return selected


def write_refresh_raw(codigo: str, payload: Dict[str, Any]) -> str:
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    raw_name = f"mp_refresh_{codigo.replace('/', '_')}_{timestamp}.json"
    raw_path = RAW_REFRESH_DIR / raw_name
    with raw_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return raw_name


def update_master_row_from_detail(
    master_row: pd.Series,
    detail: Dict[str, Any],
    award: Dict[str, Any],
    raw_refresh_file: str,
    attempts: int,
    error_msg: Optional[str],
) -> Dict[str, Any]:
    row = master_row.copy()
    old_state = normalize_scalar(row.get("estado_actual"))
    changed = False
    state_changed = False
    award_changed = False

    fields_to_update = [
        "nombre_licitacion",
        "descripcion",
        "estado_actual",
        "fecha_publicacion",
        "fecha_cierre",
        "dias_publicacion",
        "moneda",
        "monto_estimado",
        "comprador_nombre",
        "comprador_rut",
        "comprador_region",
        "comprador_comuna",
        "unidad_nombre",
        "region",
        "tipo",
        "etapas",
        "url_acta",
        "url_ficha",
    ]

    for column in fields_to_update:
        new_value = detail.get(column)
        if is_missing(new_value):
            continue
        old_value = row.get(column)
        if normalize_scalar(old_value) != normalize_scalar(new_value):
            changed = True
            if column == "estado_actual":
                state_changed = True
        row[column] = new_value

    new_state = normalize_scalar(row.get("estado_actual"))
    row["ultima_revision"] = now_str()
    row["raw_refresh_file"] = raw_refresh_file
    row["refresh_error"] = error_msg
    row["refresh_intentos"] = attempts
    row["refresh_status"] = "success" if error_msg is None else "error"

    if str(new_state) == "8":
        old_award_tuple = (
            normalize_scalar(row.get("proveedor_adjudicado_nombre")),
            normalize_scalar(row.get("proveedor_adjudicado_rut")),
            normalize_scalar(row.get("proveedor_adjudicado_id")),
            normalize_scalar(row.get("fecha_adjudicacion")),
            normalize_scalar(row.get("monto_adjudicado")),
            normalize_scalar(row.get("n_adjudicatarios")),
        )
        new_award_tuple = (
            normalize_scalar(award.get("proveedor_adjudicado_nombre")),
            normalize_scalar(award.get("proveedor_adjudicado_rut")),
            normalize_scalar(award.get("proveedor_adjudicado_id")),
            normalize_scalar(award.get("fecha_adjudicacion")),
            normalize_scalar(award.get("monto_adjudicado")),
            normalize_scalar(award.get("n_adjudicatarios")),
        )

        has_supplier_signal = any(
            value is not None
            for value in [
                normalize_scalar(award.get("proveedor_adjudicado_nombre")),
                normalize_scalar(award.get("proveedor_adjudicado_rut")),
                normalize_scalar(award.get("proveedor_adjudicado_id")),
            ]
        )

        if any(value is not None for value in new_award_tuple):
            if old_award_tuple != new_award_tuple:
                award_changed = True
                changed = True
            row["proveedor_adjudicado_nombre"] = award.get("proveedor_adjudicado_nombre")
            row["proveedor_adjudicado_rut"] = award.get("proveedor_adjudicado_rut")
            row["proveedor_adjudicado_id"] = award.get("proveedor_adjudicado_id")
            row["fecha_adjudicacion"] = award.get("fecha_adjudicacion")
            row["monto_adjudicado"] = award.get("monto_adjudicado")
            row["n_adjudicatarios"] = award.get("n_adjudicatarios")
            if has_supplier_signal:
                row["adjudicacion_capturada"] = True
                row["fecha_captura_adjudicacion"] = now_str()
                row["requiere_refresh_adjudicacion"] = False
            else:
                row["adjudicacion_capturada"] = False
                row["requiere_refresh_adjudicacion"] = True
        else:
            row["requiere_refresh_adjudicacion"] = True
    elif not coerce_bool(row.get("adjudicacion_capturada"), default=False):
        row["requiere_refresh_adjudicacion"] = True

    if changed:
        row["ultima_actualizacion_detectada"] = now_str()

    current_state = normalize_scalar(row.get("estado_actual"))
    captured = coerce_bool(row.get("adjudicacion_capturada"), default=False)
    needs_award = coerce_bool(row.get("requiere_refresh_adjudicacion"), default=True)
    if current_state in ESTADOS_TERMINALES and not (needs_award and not captured):
        row["activo_refresh"] = False
    else:
        row["activo_refresh"] = True

    return {
        "row": row,
        "changed": changed,
        "state_changed": state_changed,
        "award_changed": award_changed,
        "old_state": old_state,
        "new_state": new_state,
    }


def write_refresh_summary(summary: Dict[str, Any]) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = MASTER_DIR / f"mp_refresh_summary_{timestamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return path


def print_refresh_plan(
    master_path: Path,
    selected: pd.DataFrame,
    limit: int,
    revisit_after_days: int,
    revisit_statuses: set[str],
    only_never_refreshed: bool,
) -> None:
    codes = (
        selected.get("codigo_licitacion", pd.Series(dtype="object"))
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    preview = codes[:10]
    refresh_status = (
        selected.get("refresh_status", pd.Series([pd.NA] * len(selected), index=selected.index))
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )
    ultima_revision_dt = pd.to_datetime(
        selected.get("ultima_revision", pd.Series([pd.NaT] * len(selected), index=selected.index)),
        errors="coerce",
    )
    current_status_tokens = selected.get(
        "estado_actual",
        pd.Series([pd.NA] * len(selected), index=selected.index),
    ).apply(normalize_status_token)
    stale_threshold = pd.Timestamp.now() - pd.Timedelta(days=revisit_after_days)
    stale_revisit_mask = (
        refresh_status.eq("success")
        & ultima_revision_dt.notna()
        & ultima_revision_dt.le(stale_threshold)
        & current_status_tokens.isin(revisit_statuses)
    )
    never_refreshed = int(refresh_status.eq("").sum())
    errors_pending = int(refresh_status.eq("error").sum())
    stale_revisits = int(stale_revisit_mask.sum())
    successful_pending = int(
        refresh_status.eq("success").sum() - stale_revisits
    )

    print("[INFO] Iniciando refresh...")
    print(f"[INFO] Master objetivo: {master_path}")
    print(f"[INFO] Modo solo nunca refrescadas: {only_never_refreshed}")
    print(f"[INFO] Threshold de revisita (dias): {revisit_after_days}")
    print(f"[INFO] Estados con revisita prioritaria: {', '.join(sorted(revisit_statuses)) if revisit_statuses else '(ninguno)'}")
    print(f"[INFO] Limite de refresh: {limit}")
    print(f"[INFO] Licitaciones seleccionadas para refresh: {len(selected)}")
    print("[INFO] Desglose de seleccion:")
    print(f"[INFO] - Nunca refrescadas: {never_refreshed}")
    print(f"[INFO] - Con error pendiente: {errors_pending}")
    print(f"[INFO] - Revisitas por threshold: {stale_revisits}")
    print(f"[INFO] - Exitosas pendientes no vencidas: {successful_pending}")
    if preview:
        print(f"[INFO] Primeros codigos a refrescar: {', '.join(preview)}")
    if len(codes) > len(preview):
        print(f"[INFO] ... y {len(codes) - len(preview)} codigos mas.")


def refresh_master(
    master_path: Path = TRANSPORT_MASTER_PATH,
    history_path: Path = TRANSPORT_HISTORY_PATH,
    limit: Optional[int] = None,
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
    retry_backoff_seconds: Optional[float] = None,
    sleep_sec: Optional[float] = None,
    force_terminal_awards: Optional[bool] = None,
    revisit_after_days: Optional[int] = None,
    revisit_statuses: Optional[set[str]] = None,
    only_never_refreshed: Optional[bool] = None,
) -> Dict[str, Any]:
    ensure_dirs()
    api_key = load_api_key()
    limit = limit if limit is not None else env_int("MP_REFRESH_LIMIT", 200)
    timeout = timeout if timeout is not None else env_int("MP_REFRESH_TIMEOUT", 25)
    retries = retries if retries is not None else env_int("MP_REFRESH_MAX_RETRIES", 5)
    retry_backoff_seconds = (
        retry_backoff_seconds
        if retry_backoff_seconds is not None
        else env_float("MP_REFRESH_BACKOFF_SECONDS", 1.5)
    )
    sleep_sec = sleep_sec if sleep_sec is not None else env_float("MP_REFRESH_SLEEP_SEC", 0.6)
    force_terminal_awards = (
        force_terminal_awards
        if force_terminal_awards is not None
        else env_bool("MP_REFRESH_FORCE_TERMINAL_AWARDS", True)
    )
    revisit_after_days = (
        revisit_after_days
        if revisit_after_days is not None
        else env_int("MP_REFRESH_REVISIT_AFTER_DAYS", 7)
    )
    revisit_statuses = (
        set(revisit_statuses)
        if revisit_statuses is not None
        else env_csv_set("MP_REFRESH_REVISIT_STATUSES", {"5", "18"})
    )
    only_never_refreshed = (
        only_never_refreshed
        if only_never_refreshed is not None
        else env_bool("MP_REFRESH_ONLY_NEVER_REFRESHED", False)
    )

    df_master = ensure_master_columns(load_master(master_path))
    df_master, repaired_rows = repair_inconsistent_award_flags(df_master)
    if repaired_rows:
        print(f"[INFO] Se resetearon {repaired_rows} filas con adjudicacion capturada inconsistente.")
    df_selected = select_rows_to_refresh(
        df_master,
        limit=limit,
        force_terminal_awards=force_terminal_awards,
        revisit_after_days=revisit_after_days,
        revisit_statuses=revisit_statuses,
        only_never_refreshed=only_never_refreshed,
    )

    if df_selected.empty:
        summary = {
            "master_path": str(master_path),
            "history_path": str(history_path),
            "selected_rows": 0,
            "processed_rows": 0,
            "changed_rows": 0,
            "state_changed_rows": 0,
            "award_changed_rows": 0,
            "errors": 0,
            "updated_at": datetime.now().isoformat(),
            "refresh_revisit_after_days": revisit_after_days,
            "refresh_revisit_statuses": sorted(revisit_statuses),
            "only_never_refreshed": only_never_refreshed,
        }
        summary_path = write_refresh_summary(summary)
        summary["summary_path"] = str(summary_path)
        print(
            "[INFO] No hay licitaciones para refresh. "
            f"Todo esta al dia segun el threshold configurado de {revisit_after_days} dias."
        )
        print(f"[INFO] Resumen refresh: {summary_path}")
        return summary

    print_refresh_plan(
        master_path=master_path,
        selected=df_selected,
        limit=limit,
        revisit_after_days=revisit_after_days,
        revisit_statuses=revisit_statuses,
        only_never_refreshed=only_never_refreshed,
    )
    history_df = load_history(history_path)
    master_index = {row["codigo_licitacion"]: idx for idx, row in df_master.iterrows()}

    total_changed = 0
    total_state_changed = 0
    total_award_changed = 0
    total_errors = 0
    total_successful = 0

    for index, (_, selected_row) in enumerate(df_selected.iterrows(), start=1):
        codigo = normalize_codigo(selected_row.get("codigo_licitacion"))
        if not codigo:
            continue

        print(f"[INFO] Refresh {index}/{len(df_selected)} -> {codigo}")
        result = request_licitacion_by_codigo(
            codigo=codigo,
            api_key=api_key,
            timeout=timeout,
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

        idx = master_index[codigo]
        if not result["ok"]:
            total_errors += 1
            df_master.at[idx, "ultima_revision"] = now_str()
            df_master.at[idx, "refresh_error"] = result["error"]
            df_master.at[idx, "refresh_intentos"] = result.get("attempts", retries)
            df_master.at[idx, "refresh_status"] = "error"
            time.sleep(sleep_sec)
            continue

        raw_refresh_file = write_refresh_raw(codigo, result["payload"])
        item = extract_first_licitacion(result["payload"])
        if item is None:
            total_errors += 1
            df_master.at[idx, "ultima_revision"] = now_str()
            df_master.at[idx, "refresh_error"] = "No se encontro detalle de licitacion en payload"
            df_master.at[idx, "refresh_intentos"] = retries
            df_master.at[idx, "refresh_status"] = "error"
            df_master.at[idx, "raw_refresh_file"] = raw_refresh_file
            time.sleep(sleep_sec)
            continue

        detail = normalize_detalle_licitacion(item)
        award = extract_adjudicacion(result["payload"])
        update_result = update_master_row_from_detail(
            master_row=df_master.loc[idx].copy(),
            detail=detail,
            award=award,
            raw_refresh_file=raw_refresh_file,
            attempts=1,
            error_msg=None,
        )

        updated_row = update_result["row"]
        for column in updated_row.index:
            df_master = ensure_update_column_dtype(df_master, column, updated_row[column])
            df_master.at[idx, column] = updated_row[column]

        total_successful += 1

        if update_result["changed"]:
            total_changed += 1
        if update_result["state_changed"]:
            total_state_changed += 1
        if update_result["award_changed"]:
            total_award_changed += 1

        history_df = pd.concat(
            [
                history_df,
                pd.DataFrame(
                    [
                        {
                            "fecha_refresh": now_str(),
                            "codigo_licitacion": codigo,
                            "estado_anterior": update_result["old_state"],
                            "estado_nuevo": update_result["new_state"],
                            "cambio_estado": update_result["state_changed"],
                            "cambio_adjudicacion": update_result["award_changed"],
                            "adjudicacion_capturada": coerce_bool(updated_row.get("adjudicacion_capturada"), default=False),
                            "proveedor_adjudicado_nombre": updated_row.get("proveedor_adjudicado_nombre"),
                            "proveedor_adjudicado_rut": updated_row.get("proveedor_adjudicado_rut"),
                            "raw_refresh_file": raw_refresh_file,
                            "refresh_error": None,
                            "observacion": None,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        time.sleep(sleep_sec)

    save_master(df_master, master_path)
    save_history(history_df, history_path)

    summary = {
        "master_path": str(master_path),
        "history_path": str(history_path),
        "selected_rows": int(len(df_selected)),
        "processed_rows": int(len(df_selected)),
        "successful_rows": total_successful,
        "failed_rows": total_errors,
        "changed_rows": total_changed,
        "state_changed_rows": total_state_changed,
        "award_changed_rows": total_award_changed,
        "errors": total_errors,
        "updated_at": datetime.now().isoformat(),
        "refresh_limit": limit,
        "refresh_timeout": timeout,
        "refresh_retries": retries,
        "refresh_backoff_seconds": retry_backoff_seconds,
        "refresh_sleep_sec": sleep_sec,
        "force_terminal_awards": force_terminal_awards,
        "repaired_inconsistent_award_rows": repaired_rows,
        "refresh_revisit_after_days": revisit_after_days,
        "refresh_revisit_statuses": sorted(revisit_statuses),
        "only_never_refreshed": only_never_refreshed,
    }
    summary_path = write_refresh_summary(summary)
    summary["summary_path"] = str(summary_path)

    if total_successful > 0:
        print("[OK] Refresh completado.")
    else:
        print("[WARN] Refresh finalizado sin actualizaciones exitosas.")
    print(f"[INFO] Exitos: {total_successful}")
    print(f"[INFO] Cambios totales: {total_changed}")
    print(f"[INFO] Cambios de estado: {total_state_changed}")
    print(f"[INFO] Cambios de adjudicacion: {total_award_changed}")
    print(f"[INFO] Errores: {total_errors}")
    print(f"[INFO] Resumen refresh: {summary_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza estados y adjudicacion del master sectorial de transporte."
    )
    parser.add_argument(
        "--master-path",
        type=Path,
        default=TRANSPORT_MASTER_PATH,
        help="Master objetivo para refresh. Por defecto usa el transport master.",
    )
    parser.add_argument(
        "--history-path",
        type=Path,
        default=TRANSPORT_HISTORY_PATH,
        help="Ruta del historial de refresh.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad maxima de licitaciones a refrescar. Si no se indica, usa MP_REFRESH_LIMIT del .env.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout por request. Si no se indica, usa MP_REFRESH_TIMEOUT del .env.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=None,
        help="Reintentos por codigo. Si no se indica, usa MP_REFRESH_MAX_RETRIES del .env.",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=None,
        help="Backoff base entre reintentos. Si no se indica, usa MP_REFRESH_BACKOFF_SECONDS del .env.",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=None,
        help="Pausa entre codigos refrescados. Si no se indica, usa MP_REFRESH_SLEEP_SEC del .env.",
    )
    parser.add_argument(
        "--force-terminal-awards",
        action="store_true",
        help="Fuerza refresh de terminales si falta adjudicacion, ignorando el .env.",
    )
    parser.add_argument(
        "--revisit-after-days",
        type=int,
        default=None,
        help="Dias tras los cuales ciertos estados vuelven a subir en prioridad. Si no se indica, usa MP_REFRESH_REVISIT_AFTER_DAYS del .env.",
    )
    parser.add_argument(
        "--revisit-statuses",
        type=str,
        default=None,
        help="Estados separados por coma que vuelven a priorizarse tras X dias. Si no se indica, usa MP_REFRESH_REVISIT_STATUSES del .env.",
    )
    parser.add_argument(
        "--only-never-refreshed",
        action="store_true",
        help="Refresca solo licitaciones que aun no tienen refresh previo. Si no se indica, usa MP_REFRESH_ONLY_NEVER_REFRESHED del .env.",
    )
    args = parser.parse_args()

    revisit_statuses = None
    if args.revisit_statuses:
        revisit_statuses = {part.strip().lower() for part in args.revisit_statuses.split(",") if part.strip()}

    refresh_master(
        master_path=args.master_path,
        history_path=args.history_path,
        limit=args.limit,
        timeout=args.timeout,
        retries=args.retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        sleep_sec=args.sleep_sec,
        force_terminal_awards=args.force_terminal_awards if args.force_terminal_awards else None,
        revisit_after_days=args.revisit_after_days,
        revisit_statuses=revisit_statuses,
        only_never_refreshed=True if args.only_never_refreshed else None,
    )


if __name__ == "__main__":
    main()
