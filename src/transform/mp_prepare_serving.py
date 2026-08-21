from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from apply_transport_manual_review import TRANSPORT_MASTER_CORE_PATH


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
SERVING_DIR = DATA_DIR / "serving"

TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
DEFAULT_SERVING_MASTER_PATH = TRANSPORT_MASTER_CORE_PATH

LISTING_FIELD_DESCRIPTIONS = {
    "codigo_licitacion": "Identificador unico de la licitacion.",
    "nombre": "Titulo corto mostrado en listados.",
    "estado": "Estado textual actual o enriquecido.",
    "estado_bucket": "Bucket normalizado para filtros rapidos.",
    "fecha_publicacion": "Fecha de publicacion de la licitacion.",
    "fecha_cierre": "Fecha de cierre de la licitacion.",
    "periodo_publicacion": "Periodo YYYY-MM para agregaciones y filtros.",
    "comprador_nombre": "Nombre del organismo comprador.",
    "comprador_rut": "RUT del comprador si esta disponible.",
    "region": "Region del comprador.",
    "comuna": "Comuna del comprador.",
    "monto_estimado": "Monto estimado de referencia.",
    "monto_adjudicado": "Monto adjudicado capturado si existe.",
    "moneda": "Moneda del monto informado.",
    "transport_score": "Score de clasificacion transporte.",
    "revision_segmento": "Segmento validado manualmente.",
    "revision_prioridad": "Prioridad de negocio asignada.",
    "revision_decision": "Decision final de inclusion sectorial.",
    "flag_mixed_bundle": "Indica mezcla con otros componentes.",
    "flag_clean_transport_amount": "Indica si el monto es utilizable sin depuracion adicional.",
    "adjudicacion_capturada": "Indica si la adjudicacion ya fue capturada.",
    "requiere_refresh_adjudicacion": "Indica si aun requiere refresh de adjudicacion.",
    "fue_enriquecida": "Indica si paso por enrich de detalle.",
    "url_ficha": "URL de la ficha original.",
}

DETAIL_FIELD_DESCRIPTIONS = {
    "codigo_licitacion": "Identificador unico de la licitacion.",
    "nombre": "Nombre enriquecido o base de la licitacion.",
    "descripcion": "Descripcion completa para lectura en ficha.",
    "estado": "Estado textual actual o enriquecido.",
    "estado_bucket": "Bucket normalizado para filtros rapidos.",
    "fecha_publicacion": "Fecha de publicacion.",
    "fecha_cierre": "Fecha de cierre.",
    "dias_hasta_cierre": "Dias entre publicacion y cierre.",
    "comprador_nombre": "Organismo comprador.",
    "comprador_rut": "RUT del comprador.",
    "region": "Region del comprador.",
    "comuna": "Comuna del comprador.",
    "unidad_nombre": "Unidad compradora cuando existe.",
    "monto_estimado": "Monto estimado.",
    "monto_adjudicado": "Monto adjudicado capturado.",
    "moneda": "Moneda informada.",
    "proveedor_adjudicado_nombre": "Nombre del proveedor adjudicado.",
    "proveedor_adjudicado_rut": "RUT del proveedor adjudicado.",
    "transport_score": "Score de clasificacion transporte.",
    "transport_rule": "Regla dominante que clasifico la licitacion.",
    "revision_decision": "Decision final de inclusion sectorial.",
    "revision_segmento": "Segmento validado manualmente.",
    "revision_prioridad": "Prioridad de negocio.",
    "revision_confianza": "Confianza de la revision manual.",
    "revision_pendiente_manual": "Marca casos aun pendientes de revision.",
    "flag_mixed_bundle": "Marca mezcla de transporte con otros componentes.",
    "flag_clean_transport_amount": "Indica si el monto puede usarse directamente.",
    "adjudicacion_capturada": "Indica si la adjudicacion ya fue capturada.",
    "requiere_refresh_adjudicacion": "Indica si aun requiere refresh.",
    "fue_enriquecida": "Indica si paso por enrich de detalle.",
    "ultima_revision": "Ultima revision o refresh conocida.",
    "ultima_actualizacion_detectada": "Ultima actualizacion detectada en el master.",
    "url_ficha": "URL a la ficha original.",
}


def load_transport_master(master_path: Path) -> pd.DataFrame:
    if not master_path.exists():
        raise FileNotFoundError(f"No existe transport master: {master_path}")
    return pd.read_csv(master_path, encoding="utf-8-sig")


def resolve_master_path(master_path: Path | None = None) -> Path:
    if master_path is not None:
        return master_path
    if DEFAULT_SERVING_MASTER_PATH.exists():
        return DEFAULT_SERVING_MASTER_PATH
    return TRANSPORT_MASTER_PATH


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def coerce_bool(series: pd.Series) -> pd.Series:
    return (
        series.fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "si", "yes"})
    )


def parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def parse_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def first_non_null(df: pd.DataFrame, primary: str, fallback: str) -> pd.Series:
    primary_series = df[primary] if primary in df.columns else pd.Series([pd.NA] * len(df), index=df.index)
    fallback_series = df[fallback] if fallback in df.columns else pd.Series([pd.NA] * len(df), index=df.index)
    return primary_series.where(primary_series.notna(), fallback_series)


def classify_estado_bucket(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    normalized = normalize_text(series).str.lower()
    normalized = normalized.where(numeric.isna(), numeric.astype("Int64").astype(str).str.lower())
    mapping = {
        "5": "publicada",
        "6": "cerrada",
        "7": "desierta",
        "8": "adjudicada",
        "18": "revocada",
        "19": "suspendida",
        "publicada": "publicada",
        "cerrada": "cerrada",
        "adjudicada": "adjudicada",
        "revocada": "revocada",
        "suspendida": "suspendida",
    }
    return normalized.map(mapping).fillna("otro")


def build_serving_dataset(df: pd.DataFrame) -> pd.DataFrame:
    serving = pd.DataFrame(index=df.index)

    serving["codigo_licitacion"] = normalize_text(df.get("codigo_licitacion", pd.Series([pd.NA] * len(df))))
    serving["nombre"] = normalize_text(first_non_null(df, "detalle_nombre", "nombre_licitacion"))
    serving["descripcion"] = normalize_text(first_non_null(df, "detalle_descripcion", "descripcion"))
    serving["estado"] = normalize_text(first_non_null(df, "detalle_estado", "estado_actual"))
    serving["estado_bucket"] = classify_estado_bucket(first_non_null(df, "detalle_codigo_estado", "estado_actual"))
    serving["fecha_publicacion"] = parse_datetime(first_non_null(df, "detalle_fecha_publicacion", "fecha_publicacion"))
    serving["fecha_cierre"] = parse_datetime(first_non_null(df, "detalle_fecha_cierre", "fecha_cierre"))
    serving["comprador_nombre"] = normalize_text(first_non_null(df, "detalle_comprador_nombre", "comprador_nombre"))
    serving["comprador_rut"] = normalize_text(first_non_null(df, "detalle_comprador_rut", "comprador_rut"))
    serving["region"] = normalize_text(first_non_null(df, "detalle_comprador_region", "comprador_region"))
    serving["comuna"] = normalize_text(first_non_null(df, "detalle_comprador_comuna", "comprador_comuna"))
    serving["unidad_nombre"] = normalize_text(first_non_null(df, "detalle_unidad_nombre", "unidad_nombre"))
    serving["monto_estimado"] = parse_numeric(first_non_null(df, "detalle_monto_estimado", "monto_estimado"))
    serving["monto_adjudicado"] = parse_numeric(df.get("monto_adjudicado", pd.Series([pd.NA] * len(df))))
    serving["moneda"] = normalize_text(first_non_null(df, "detalle_moneda", "moneda"))
    serving["url_ficha"] = normalize_text(first_non_null(df, "detalle_url_ficha", "url_ficha"))
    serving["es_transporte"] = coerce_bool(df.get("es_transporte", pd.Series([True] * len(df))))
    serving["transport_score"] = parse_numeric(df.get("transport_score", pd.Series([pd.NA] * len(df))))
    serving["transport_rule"] = normalize_text(df.get("transport_rule", pd.Series([pd.NA] * len(df))))
    serving["revision_decision"] = normalize_text(df.get("revision_decision_transdata", pd.Series([pd.NA] * len(df)))).str.upper()
    serving["revision_segmento"] = normalize_text(df.get("revision_segmento_validado", pd.Series([pd.NA] * len(df))))
    serving["revision_prioridad"] = normalize_text(df.get("revision_prioridad_negocio", pd.Series([pd.NA] * len(df)))).str.upper()
    serving["revision_confianza"] = normalize_text(df.get("revision_confianza", pd.Series([pd.NA] * len(df)))).str.upper()
    serving["revision_pendiente_manual"] = coerce_bool(df.get("revision_pending_manual", pd.Series([False] * len(df))))
    serving["flag_mixed_bundle"] = coerce_bool(df.get("flag_mixed_bundle", pd.Series([False] * len(df))))
    serving["flag_clean_transport_amount"] = coerce_bool(df.get("flag_clean_transport_amount", pd.Series([False] * len(df))))
    serving["fue_enriquecida"] = coerce_bool(df.get("enriched", pd.Series([False] * len(df))))
    serving["adjudicacion_capturada"] = coerce_bool(df.get("adjudicacion_capturada", pd.Series([False] * len(df))))
    serving["proveedor_adjudicado_nombre"] = normalize_text(df.get("proveedor_adjudicado_nombre", pd.Series([pd.NA] * len(df))))
    serving["proveedor_adjudicado_rut"] = normalize_text(df.get("proveedor_adjudicado_rut", pd.Series([pd.NA] * len(df))))
    serving["requiere_refresh_adjudicacion"] = coerce_bool(df.get("requiere_refresh_adjudicacion", pd.Series([False] * len(df))))
    serving["ultima_revision"] = normalize_text(df.get("ultima_revision", pd.Series([pd.NA] * len(df))))
    serving["ultima_actualizacion_detectada"] = normalize_text(df.get("ultima_actualizacion_detectada", pd.Series([pd.NA] * len(df))))
    serving["periodo_publicacion"] = serving["fecha_publicacion"].dt.to_period("M").astype(str)
    serving["dias_hasta_cierre"] = (serving["fecha_cierre"] - serving["fecha_publicacion"]).dt.days

    serving = serving.sort_values(
        by=["fecha_publicacion", "codigo_licitacion"],
        ascending=[False, True],
        na_position="last",
    ).reset_index(drop=True)

    return serving


def build_app_listing_view(serving_df: pd.DataFrame) -> pd.DataFrame:
    preferred_columns = [
        "codigo_licitacion",
        "nombre",
        "estado",
        "estado_bucket",
        "fecha_publicacion",
        "fecha_cierre",
        "periodo_publicacion",
        "comprador_nombre",
        "comprador_rut",
        "region",
        "comuna",
        "monto_estimado",
        "monto_adjudicado",
        "moneda",
        "transport_score",
        "revision_segmento",
        "revision_prioridad",
        "revision_decision",
        "flag_mixed_bundle",
        "flag_clean_transport_amount",
        "adjudicacion_capturada",
        "requiere_refresh_adjudicacion",
        "fue_enriquecida",
        "url_ficha",
    ]
    existing = [column for column in preferred_columns if column in serving_df.columns]
    return serving_df[existing].copy()


def build_app_detail_view(serving_df: pd.DataFrame) -> pd.DataFrame:
    preferred_columns = [
        "codigo_licitacion",
        "nombre",
        "descripcion",
        "estado",
        "estado_bucket",
        "fecha_publicacion",
        "fecha_cierre",
        "dias_hasta_cierre",
        "comprador_nombre",
        "comprador_rut",
        "region",
        "comuna",
        "unidad_nombre",
        "monto_estimado",
        "monto_adjudicado",
        "moneda",
        "proveedor_adjudicado_nombre",
        "proveedor_adjudicado_rut",
        "transport_score",
        "transport_rule",
        "revision_decision",
        "revision_segmento",
        "revision_prioridad",
        "revision_confianza",
        "revision_pendiente_manual",
        "flag_mixed_bundle",
        "flag_clean_transport_amount",
        "adjudicacion_capturada",
        "requiere_refresh_adjudicacion",
        "fue_enriquecida",
        "ultima_revision",
        "ultima_actualizacion_detectada",
        "url_ficha",
    ]
    existing = [column for column in preferred_columns if column in serving_df.columns]
    return serving_df[existing].copy()


def build_app_contract(
    serving_df: pd.DataFrame,
    listing_df: pd.DataFrame,
    detail_df: pd.DataFrame,
) -> Dict[str, object]:
    def field_records(columns: List[str], descriptions: Dict[str, str]) -> List[Dict[str, object]]:
        records: List[Dict[str, object]] = []
        for column in columns:
            records.append(
                {
                    "name": column,
                    "description": descriptions.get(column, ""),
                    "dtype": str(serving_df[column].dtype) if column in serving_df.columns else "unknown",
                    "nullable": bool(serving_df[column].isna().any()) if column in serving_df.columns else True,
                }
            )
        return records

    return {
        "generated_at": datetime.now().isoformat(),
        "source_preference": {
            "primary": str(DEFAULT_SERVING_MASTER_PATH),
            "fallback": str(TRANSPORT_MASTER_PATH),
        },
        "views": {
            "listing": {
                "purpose": "Vista liviana para tablas, busqueda y resultados paginados.",
                "primary_key": "codigo_licitacion",
                "fields": field_records(list(listing_df.columns), LISTING_FIELD_DESCRIPTIONS),
                "recommended_default_sort": ["fecha_publicacion desc", "codigo_licitacion asc"],
                "recommended_filters": [
                    "estado_bucket",
                    "region",
                    "comuna",
                    "periodo_publicacion",
                    "revision_segmento",
                    "revision_prioridad",
                    "revision_decision",
                    "adjudicacion_capturada",
                    "requiere_refresh_adjudicacion",
                ],
            },
            "detail": {
                "purpose": "Vista detallada para ficha individual y exploracion profunda.",
                "primary_key": "codigo_licitacion",
                "fields": field_records(list(detail_df.columns), DETAIL_FIELD_DESCRIPTIONS),
                "recommended_related_lookup": "codigo_licitacion",
            },
        },
        "business_notes": {
            "mixed_bundle_policy": (
                "Si flag_mixed_bundle es true, el monto no debe usarse directamente para market sizing "
                "sin depuracion adicional."
            ),
            "manual_review_policy": (
                "revision_decision y revision_segmento resumen la capa de revision manual aplicada al core."
            ),
            "refresh_policy": (
                "requiere_refresh_adjudicacion marca licitaciones cuyo detalle de adjudicacion aun puede cambiar."
            ),
        },
    }


def unique_non_empty(series: pd.Series, limit: int = 500) -> List[str]:
    values = normalize_text(series)
    values = values[values != ""].drop_duplicates().sort_values()
    return values.head(limit).tolist()


def build_manifest(serving_df: pd.DataFrame) -> Dict[str, object]:
    return {
        "generated_at": datetime.now().isoformat(),
        "rows": int(len(serving_df)),
        "columns": list(serving_df.columns),
        "views": {
            "listing": "transport_app_listing_latest.csv",
            "detail": "transport_app_detail_latest.csv",
            "dataset": "transport_dataset_latest.csv",
        },
        "filters": {
            "estado_bucket": unique_non_empty(serving_df["estado_bucket"]),
            "region": unique_non_empty(serving_df["region"]),
            "comuna": unique_non_empty(serving_df["comuna"]),
            "periodo_publicacion": unique_non_empty(serving_df["periodo_publicacion"]),
            "revision_segmento": unique_non_empty(serving_df["revision_segmento"]),
            "revision_prioridad": unique_non_empty(serving_df["revision_prioridad"]),
            "revision_decision": unique_non_empty(serving_df["revision_decision"]),
        },
        "stats": {
            "enriched_rows": int(serving_df["fue_enriquecida"].sum()),
            "adjudicacion_capturada_rows": int(serving_df["adjudicacion_capturada"].sum()),
            "refresh_pending_rows": int(serving_df["requiere_refresh_adjudicacion"].sum()),
            "mixed_bundle_rows": int(serving_df["flag_mixed_bundle"].sum()),
            "manual_review_pending_rows": int(serving_df["revision_pendiente_manual"].sum()),
            "fecha_publicacion_min": (
                serving_df["fecha_publicacion"].min().isoformat()
                if pd.notna(serving_df["fecha_publicacion"].min())
                else None
            ),
            "fecha_publicacion_max": (
                serving_df["fecha_publicacion"].max().isoformat()
                if pd.notna(serving_df["fecha_publicacion"].max())
                else None
            ),
        },
        "provisional_note": (
            "Esta capa de serving es derivada del transport master core cuando existe, "
            "con fallback al transport master amplio. Puede ajustarse cuando el refresh "
            "estabilice estados y adjudicaciones."
        ),
    }


def write_outputs(
    serving_df: pd.DataFrame,
    listing_df: pd.DataFrame,
    detail_df: pd.DataFrame,
    manifest: Dict[str, object],
    contract: Dict[str, object],
    output_dir: Path,
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    latest_csv = output_dir / "transport_dataset_latest.csv"
    latest_json = output_dir / "transport_dataset_manifest_latest.json"
    snapshot_csv = output_dir / f"transport_dataset_{timestamp}.csv"
    snapshot_json = output_dir / f"transport_dataset_manifest_{timestamp}.json"
    latest_contract_json = output_dir / "transport_app_contract_latest.json"
    snapshot_contract_json = output_dir / f"transport_app_contract_{timestamp}.json"
    latest_listing_csv = output_dir / "transport_app_listing_latest.csv"
    snapshot_listing_csv = output_dir / f"transport_app_listing_{timestamp}.csv"
    latest_detail_csv = output_dir / "transport_app_detail_latest.csv"
    snapshot_detail_csv = output_dir / f"transport_app_detail_{timestamp}.csv"

    serving_df.to_csv(latest_csv, index=False, encoding="utf-8-sig")
    serving_df.to_csv(snapshot_csv, index=False, encoding="utf-8-sig")
    listing_df.to_csv(latest_listing_csv, index=False, encoding="utf-8-sig")
    listing_df.to_csv(snapshot_listing_csv, index=False, encoding="utf-8-sig")
    detail_df.to_csv(latest_detail_csv, index=False, encoding="utf-8-sig")
    detail_df.to_csv(snapshot_detail_csv, index=False, encoding="utf-8-sig")

    for path in [latest_json, snapshot_json]:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2)

    for path in [latest_contract_json, snapshot_contract_json]:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(contract, handle, ensure_ascii=False, indent=2)

    return {
        "latest_dataset_path": latest_csv,
        "latest_manifest_path": latest_json,
        "snapshot_dataset_path": snapshot_csv,
        "snapshot_manifest_path": snapshot_json,
        "latest_contract_path": latest_contract_json,
        "snapshot_contract_path": snapshot_contract_json,
        "latest_listing_path": latest_listing_csv,
        "snapshot_listing_path": snapshot_listing_csv,
        "latest_detail_path": latest_detail_csv,
        "snapshot_detail_path": snapshot_detail_csv,
    }


def prepare_serving(master_path: Path | None = None, output_dir: Path = SERVING_DIR) -> Dict[str, object]:
    resolved_master_path = resolve_master_path(master_path)
    master_df = load_transport_master(resolved_master_path)
    serving_df = build_serving_dataset(master_df)
    listing_df = build_app_listing_view(serving_df)
    detail_df = build_app_detail_view(serving_df)
    manifest = build_manifest(serving_df)
    contract = build_app_contract(serving_df, listing_df, detail_df)
    outputs = write_outputs(serving_df, listing_df, detail_df, manifest, contract, output_dir)

    result = {
        "master_path": str(resolved_master_path),
        "output_dir": str(output_dir),
        "rows": int(len(serving_df)),
        **{key: str(value) for key, value in outputs.items()},
        **manifest,
    }

    print("[OK] Capa de serving generada.")
    print(f"[INFO] Filas serving: {result['rows']}")
    print(f"[INFO] Dataset latest: {result['latest_dataset_path']}")
    print(f"[INFO] Listing latest: {result['latest_listing_path']}")
    print(f"[INFO] Detail latest: {result['latest_detail_path']}")
    print(f"[INFO] Manifest latest: {result['latest_manifest_path']}")
    print(f"[INFO] Contract latest: {result['latest_contract_path']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Prepara una capa de serving derivada del transport master."
    )
    parser.add_argument(
        "--master-path",
        type=Path,
        default=None,
        help="Ruta al master fuente. Si no se indica, prioriza transport master core.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SERVING_DIR,
        help="Directorio de salida para artefactos de serving.",
    )
    args = parser.parse_args()

    prepare_serving(master_path=args.master_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
