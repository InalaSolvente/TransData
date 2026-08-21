from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from apply_transport_manual_review import TRANSPORT_MASTER_CORE_PATH


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
ANALYTICS_DIR = DATA_DIR / "analytics"

TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
DEFAULT_ANALYTICS_MASTER_PATH = TRANSPORT_MASTER_CORE_PATH


def load_transport_master(master_path: Path) -> pd.DataFrame:
    if not master_path.exists():
        raise FileNotFoundError(f"No existe transport master: {master_path}")
    return pd.read_csv(master_path, encoding="utf-8-sig")


def resolve_master_path(master_path: Path | None = None) -> Path:
    if master_path is not None:
        return master_path
    if DEFAULT_ANALYTICS_MASTER_PATH.exists():
        return DEFAULT_ANALYTICS_MASTER_PATH
    return TRANSPORT_MASTER_PATH


def normalize_text_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def choose_first_non_null(df: pd.DataFrame, primary: str, fallback: str) -> pd.Series:
    primary_series = df[primary] if primary in df.columns else pd.Series([pd.NA] * len(df), index=df.index)
    fallback_series = df[fallback] if fallback in df.columns else pd.Series([pd.NA] * len(df), index=df.index)
    return primary_series.where(primary_series.notna(), fallback_series)


def parse_datetime_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def parse_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def classify_status_group(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    normalized = series.fillna("").astype(str).str.strip().str.lower()
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
        "desierta": "desierta",
        "adjudicada": "adjudicada",
        "revocada": "revocada",
        "suspendida": "suspendida",
    }
    return normalized.map(mapping).fillna("otro")


def derive_analytic_dataset(df: pd.DataFrame) -> pd.DataFrame:
    analytic = df.copy()

    analytic["fecha_publicacion_final"] = parse_datetime_series(
        choose_first_non_null(analytic, "detalle_fecha_publicacion", "fecha_publicacion")
    )
    analytic["fecha_cierre_final"] = parse_datetime_series(
        choose_first_non_null(analytic, "detalle_fecha_cierre", "fecha_cierre")
    )
    analytic["monto_estimado_final"] = parse_numeric_series(
        choose_first_non_null(analytic, "detalle_monto_estimado", "monto_estimado")
    )
    analytic["estado_final"] = choose_first_non_null(analytic, "detalle_estado", "estado_actual")
    analytic["codigo_estado_final"] = parse_numeric_series(
        choose_first_non_null(analytic, "detalle_codigo_estado", "estado_actual")
    )
    analytic["comprador_nombre_final"] = normalize_text_series(
        choose_first_non_null(analytic, "detalle_comprador_nombre", "comprador_nombre")
    )
    analytic["comprador_region_final"] = normalize_text_series(
        choose_first_non_null(analytic, "detalle_comprador_region", "comprador_region")
    )
    analytic["comprador_comuna_final"] = normalize_text_series(
        choose_first_non_null(analytic, "detalle_comprador_comuna", "comprador_comuna")
    )
    analytic["descripcion_final"] = normalize_text_series(
        choose_first_non_null(analytic, "detalle_descripcion", "descripcion")
    )
    analytic["nombre_licitacion_final"] = normalize_text_series(
        choose_first_non_null(analytic, "detalle_nombre", "nombre_licitacion")
    )

    analytic["estado_grupo"] = classify_status_group(
        choose_first_non_null(analytic, "detalle_codigo_estado", "estado_actual")
    )
    analytic["publicacion_anio"] = analytic["fecha_publicacion_final"].dt.year
    analytic["publicacion_mes"] = analytic["fecha_publicacion_final"].dt.month
    analytic["publicacion_periodo"] = analytic["fecha_publicacion_final"].dt.to_period("M").astype(str)
    analytic["cierre_anio"] = analytic["fecha_cierre_final"].dt.year
    analytic["cierre_mes"] = analytic["fecha_cierre_final"].dt.month
    analytic["dias_hasta_cierre"] = (
        analytic["fecha_cierre_final"] - analytic["fecha_publicacion_final"]
    ).dt.days

    analytic["monto_adjudicado_num"] = parse_numeric_series(analytic.get("monto_adjudicado", pd.Series([pd.NA] * len(analytic))))
    analytic["tiene_monto_estimado"] = analytic["monto_estimado_final"].notna()
    analytic["tiene_adjudicacion_capturada"] = (
        analytic.get("adjudicacion_capturada", pd.Series([False] * len(analytic)))
        .fillna(False)
        .astype(str)
        .str.lower()
        .isin({"true", "1", "si", "yes"})
    )
    analytic["fue_enriquecida"] = (
        analytic.get("enriched", pd.Series([False] * len(analytic)))
        .fillna(False)
        .astype(str)
        .str.lower()
        .isin({"true", "1", "si", "yes"})
    )
    analytic["requiere_refresh_adjudicacion_flag"] = (
        analytic.get("requiere_refresh_adjudicacion", pd.Series([False] * len(analytic)))
        .fillna(False)
        .astype(str)
        .str.lower()
        .isin({"true", "1", "si", "yes"})
    )

    analytic["buyer_key"] = (
        analytic["comprador_nombre_final"].str.lower()
        + " | "
        + normalize_text_series(analytic.get("comprador_rut", pd.Series([pd.NA] * len(analytic)))).str.lower()
    )

    preferred_columns = [
        "codigo_licitacion",
        "nombre_licitacion_final",
        "descripcion_final",
        "estado_final",
        "codigo_estado_final",
        "estado_grupo",
        "fecha_publicacion_final",
        "fecha_cierre_final",
        "publicacion_anio",
        "publicacion_mes",
        "publicacion_periodo",
        "cierre_anio",
        "cierre_mes",
        "dias_hasta_cierre",
        "monto_estimado_final",
        "monto_adjudicado_num",
        "comprador_nombre_final",
        "comprador_rut",
        "comprador_region_final",
        "comprador_comuna_final",
        "buyer_key",
        "fue_enriquecida",
        "tiene_adjudicacion_capturada",
        "requiere_refresh_adjudicacion_flag",
        "transport_score",
        "transport_positive_hits",
        "transport_negative_hits",
        "transport_match_fields",
        "transport_rule",
        "veces_vista",
        "ultima_revision",
        "ultima_actualizacion_detectada",
    ]
    existing_preferred = [column for column in preferred_columns if column in analytic.columns]
    remaining = [column for column in analytic.columns if column not in existing_preferred]
    return analytic[existing_preferred + remaining]


def aggregate_by_buyer(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["buyer_key", "comprador_nombre_final", "comprador_rut", "comprador_region_final"], dropna=False)
        .agg(
            licitaciones=("codigo_licitacion", "nunique"),
            monto_estimado_total=("monto_estimado_final", "sum"),
            monto_adjudicado_total=("monto_adjudicado_num", "sum"),
            adjudicadas=("tiene_adjudicacion_capturada", "sum"),
            enriquecidas=("fue_enriquecida", "sum"),
        )
        .reset_index()
        .sort_values(by=["licitaciones", "monto_estimado_total"], ascending=[False, False], na_position="last")
    )
    return grouped


def aggregate_by_region_period(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["comprador_region_final", "publicacion_periodo", "estado_grupo"], dropna=False)
        .agg(
            licitaciones=("codigo_licitacion", "nunique"),
            monto_estimado_total=("monto_estimado_final", "sum"),
            monto_adjudicado_total=("monto_adjudicado_num", "sum"),
        )
        .reset_index()
        .sort_values(by=["publicacion_periodo", "comprador_region_final", "estado_grupo"])
    )
    return grouped


def build_summary(df: pd.DataFrame) -> Dict[str, object]:
    return {
        "generated_at": datetime.now().isoformat(),
        "rows": int(len(df)),
        "unique_codigos": int(df["codigo_licitacion"].nunique()) if "codigo_licitacion" in df.columns else 0,
        "enriched_rows": int(df["fue_enriquecida"].sum()) if "fue_enriquecida" in df.columns else 0,
        "adjudicacion_capturada_rows": int(df["tiene_adjudicacion_capturada"].sum()) if "tiene_adjudicacion_capturada" in df.columns else 0,
        "refresh_pending_rows": int(df["requiere_refresh_adjudicacion_flag"].sum()) if "requiere_refresh_adjudicacion_flag" in df.columns else 0,
        "publicacion_min": (
            df["fecha_publicacion_final"].min().isoformat() if "fecha_publicacion_final" in df.columns and pd.notna(df["fecha_publicacion_final"].min()) else None
        ),
        "publicacion_max": (
            df["fecha_publicacion_final"].max().isoformat() if "fecha_publicacion_final" in df.columns and pd.notna(df["fecha_publicacion_final"].max()) else None
        ),
    }


def write_outputs(
    analytic_df: pd.DataFrame,
    buyer_df: pd.DataFrame,
    region_period_df: pd.DataFrame,
    summary: Dict[str, object],
    output_dir: Path,
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    analytic_path = output_dir / f"transport_master_analytic_{timestamp}.csv"
    buyer_path = output_dir / f"transport_agg_buyers_{timestamp}.csv"
    region_period_path = output_dir / f"transport_agg_region_period_{timestamp}.csv"
    summary_path = output_dir / f"transport_analytics_summary_{timestamp}.json"

    analytic_df.to_csv(analytic_path, index=False, encoding="utf-8-sig")
    buyer_df.to_csv(buyer_path, index=False, encoding="utf-8-sig")
    region_period_df.to_csv(region_period_path, index=False, encoding="utf-8-sig")

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    return {
        "analytic_path": analytic_path,
        "buyer_path": buyer_path,
        "region_period_path": region_period_path,
        "summary_path": summary_path,
    }


def prepare_analytics(
    master_path: Path | None = None,
    output_dir: Path = ANALYTICS_DIR,
) -> Dict[str, object]:
    resolved_master_path = resolve_master_path(master_path)
    transport_master = load_transport_master(resolved_master_path)
    analytic_df = derive_analytic_dataset(transport_master)
    buyer_df = aggregate_by_buyer(analytic_df)
    region_period_df = aggregate_by_region_period(analytic_df)
    summary = build_summary(analytic_df)
    outputs = write_outputs(analytic_df, buyer_df, region_period_df, summary, output_dir)

    result = {
        "master_path": str(master_path),
        "resolved_master_path": str(resolved_master_path),
        "output_dir": str(output_dir),
        **summary,
        **{key: str(path) for key, path in outputs.items()},
        "provisional_note": (
            "Esta capa analitica es derivada del transport master core cuando existe, "
            "con fallback al transport master amplio. Puede cambiar cuando el refresh "
            "de estados y adjudicaciones se estabilice."
        ),
    }

    print("[OK] Base analitica generada.")
    print(f"[INFO] Filas analiticas: {result['rows']}")
    print(f"[INFO] Archivo analitico: {result['analytic_path']}")
    print(f"[INFO] Agregado compradores: {result['buyer_path']}")
    print(f"[INFO] Agregado region-periodo: {result['region_period_path']}")
    print(f"[INFO] Resumen: {result['summary_path']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Prepara una capa analitica derivada del transport master."
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
        default=ANALYTICS_DIR,
        help="Directorio de salida para artefactos analiticos.",
    )
    args = parser.parse_args()

    prepare_analytics(master_path=args.master_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
