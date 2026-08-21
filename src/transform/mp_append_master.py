import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
MASTER_DIR = ROOT / "data" / "master"
MASTER_PATH = MASTER_DIR / "licitaciones_master.csv"


REQUIRED_COLS = [
    "codigo_licitacion",
    "nombre_licitacion",
    "descripcion",
    "estado_actual",
    "estado_consultado",
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
    "fecha_consulta",
    "raw_file",
    "ingest_start_day",
    "ingest_end_day",
    "ingest_timestamp",
    "parse_timestamp",
    "ultima_revision",
    "registro_fuente",
    "duplicados_en_raw",
    "es_duplicado_raw",
]

MASTER_COLS = [
    "primera_vez_vista",
    "ultima_actualizacion_detectada",
    "veces_vista",
    "enriched",
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
]


def now_str():
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def find_processed_files(processed_dir=PROCESSED_DIR, latest_only=False):
    files = sorted(
        Path(processed_dir).glob("licitaciones_processed_*.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    if latest_only and files:
        return [files[-1]]
    return files


def load_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def ensure_columns(df, columns):
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def normalize_code_series(series):
    return series.astype(str).str.strip()


def prepare_processed_df(df):
    df = df.copy()
    df = ensure_columns(df, REQUIRED_COLS)
    df = ensure_columns(df, MASTER_COLS)

    df["codigo_licitacion"] = normalize_code_series(df["codigo_licitacion"])
    df = df[df["codigo_licitacion"].notna()]
    df = df[df["codigo_licitacion"] != ""]
    df = df[df["codigo_licitacion"].str.lower() != "nan"]

    ts = now_str()
    df["primera_vez_vista"] = ts
    df["ultima_actualizacion_detectada"] = ts
    df["veces_vista"] = 1
    df["enriched"] = False
    df["activo_refresh"] = True
    df["adjudicacion_capturada"] = False
    df["requiere_refresh_adjudicacion"] = True
    df["ultima_revision"] = ts

    return df


def prepare_master_df(df):
    df = df.copy()
    df = ensure_columns(df, REQUIRED_COLS)
    df = ensure_columns(df, MASTER_COLS)
    df["codigo_licitacion"] = normalize_code_series(df["codigo_licitacion"])
    return df


def is_missing(value):
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null"}:
        return True
    return False


def normalize_compare_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def has_meaningful_change(old_value, new_value):
    old_n = normalize_compare_value(old_value)
    new_n = normalize_compare_value(new_value)

    if old_n is None and new_n is None:
        return False
    if old_n is None and new_n is not None:
        return True
    if old_n is not None and new_n is None:
        return False
    return old_n != new_n


def coerce_bool(value, default=False):
    if pd.isna(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "1", "si", "yes"}:
            return True
        if s in {"false", "0", "no"}:
            return False
    return default


def merge_row(old_row, new_row):
    merged = old_row.copy()
    changed = False

    protected_fields = {
        "primera_vez_vista",
        "veces_vista",
        "enriched",
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
    }

    for col in new_row.index:
        if col in protected_fields:
            continue

        old_val = old_row[col] if col in old_row.index else pd.NA
        new_val = new_row[col]

        if not is_missing(new_val):
            if has_meaningful_change(old_val, new_val):
                changed = True
            merged[col] = new_val
        elif col not in merged.index:
            merged[col] = old_val

    if is_missing(merged.get("primera_vez_vista")):
        merged["primera_vez_vista"] = now_str()
        changed = True
    else:
        merged["primera_vez_vista"] = old_row.get("primera_vez_vista")

    try:
        old_count = int(float(old_row.get("veces_vista", 0)))
    except Exception:
        old_count = 0
    merged["veces_vista"] = old_count + 1

    merged["enriched"] = coerce_bool(old_row.get("enriched"), default=False)
    merged["activo_refresh"] = coerce_bool(old_row.get("activo_refresh"), default=True)

    for col in [
        "proveedor_adjudicado_nombre",
        "proveedor_adjudicado_rut",
        "proveedor_adjudicado_id",
        "fecha_adjudicacion",
        "monto_adjudicado",
        "n_adjudicatarios",
        "fecha_captura_adjudicacion",
    ]:
        merged[col] = old_row.get(col)

    merged["adjudicacion_capturada"] = coerce_bool(
        old_row.get("adjudicacion_capturada"), default=False
    )
    merged["requiere_refresh_adjudicacion"] = coerce_bool(
        old_row.get("requiere_refresh_adjudicacion"), default=True
    )
    merged["ultima_revision"] = now_str()

    if changed:
        merged["ultima_actualizacion_detectada"] = now_str()
    else:
        merged["ultima_actualizacion_detectada"] = old_row.get("ultima_actualizacion_detectada")

    return merged, changed


def merge_processed_into_master(df_processed, df_master=None):
    df_processed = prepare_processed_df(df_processed)

    if df_processed.empty:
        stats = {"nuevas": 0, "actualizadas": 0, "sin_cambios": 0, "total_final": 0}
        if df_master is not None:
            stats["total_final"] = len(df_master)
            return prepare_master_df(df_master), stats
        return df_processed, stats

    df_processed = df_processed.drop_duplicates(subset=["codigo_licitacion"], keep="last")

    if df_master is None or df_master.empty:
        return df_processed, {
            "nuevas": len(df_processed),
            "actualizadas": 0,
            "sin_cambios": 0,
            "total_final": len(df_processed),
        }

    df_master = prepare_master_df(df_master)
    master_by_code = {row["codigo_licitacion"]: row for _, row in df_master.iterrows()}

    result_rows = []
    seen_codes = set()
    nuevas = 0
    actualizadas = 0
    sin_cambios = 0

    for _, new_row in df_processed.iterrows():
        code = new_row["codigo_licitacion"]
        seen_codes.add(code)

        if code not in master_by_code:
            result_rows.append(new_row)
            nuevas += 1
        else:
            merged_row, changed = merge_row(master_by_code[code], new_row)
            result_rows.append(merged_row)
            if changed:
                actualizadas += 1
            else:
                sin_cambios += 1

    for _, old_row in df_master.iterrows():
        if old_row["codigo_licitacion"] not in seen_codes:
            result_rows.append(old_row)

    df_result = pd.DataFrame(result_rows)
    df_result = df_result.drop_duplicates(subset=["codigo_licitacion"], keep="first")

    return df_result, {
        "nuevas": nuevas,
        "actualizadas": actualizadas,
        "sin_cambios": sin_cambios,
        "total_final": len(df_result),
    }


def order_master_columns(df):
    preferred = [
        "codigo_licitacion",
        "nombre_licitacion",
        "descripcion",
        "estado_actual",
        "estado_consultado",
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
        "fecha_consulta",
        "primera_vez_vista",
        "ultima_revision",
        "ultima_actualizacion_detectada",
        "veces_vista",
        "enriched",
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
        "raw_file",
        "ingest_start_day",
        "ingest_end_day",
        "ingest_timestamp",
        "parse_timestamp",
        "registro_fuente",
        "duplicados_en_raw",
        "es_duplicado_raw",
    ]
    existing_preferred = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_preferred]
    return df[existing_preferred + remaining]


def write_append_summary(summary):
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = MASTER_DIR / f"mp_append_master_summary_{timestamp}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return path


def append_processed_files(processed_files, master_path=MASTER_PATH):
    MASTER_DIR.mkdir(parents=True, exist_ok=True)

    if Path(master_path).exists():
        print(f"[INFO] Cargando master existente: {master_path}")
        df_master = load_csv(master_path)
    else:
        print("[INFO] No existe master previo. Se creara uno nuevo.")
        df_master = None

    cumulative_stats = {
        "nuevas": 0,
        "actualizadas": 0,
        "sin_cambios": 0,
        "total_final": 0,
    }
    file_results = []

    for i, processed_path in enumerate(processed_files, start=1):
        print(f"\n[INFO] Append {i}/{len(processed_files)}: {processed_path.name}")
        df_processed = load_csv(processed_path)
        df_master, stats = merge_processed_into_master(df_processed, df_master)

        for key in ["nuevas", "actualizadas", "sin_cambios"]:
            cumulative_stats[key] += stats[key]
        cumulative_stats["total_final"] = stats["total_final"]

        file_results.append({
            "processed_file": str(processed_path),
            **stats,
        })

        print(
            "[INFO] Nuevas={nuevas} Actualizadas={actualizadas} "
            "SinCambios={sin_cambios} Total={total_final}".format(**stats)
        )

    if df_master is None:
        df_master = pd.DataFrame(columns=REQUIRED_COLS + MASTER_COLS)

    df_master = order_master_columns(df_master)
    df_master.to_csv(master_path, index=False, encoding="utf-8-sig")

    summary = {
        "metadata": {
            "type": "append_master_summary",
            "generated_at": datetime.now().isoformat(),
            "master_path": str(master_path),
        },
        "results": {
            "processed_files": len(processed_files),
            **cumulative_stats,
        },
        "files": file_results,
    }
    summary_path = write_append_summary(summary)

    print(f"\n[OK] Master guardado en: {master_path}")
    print(f"[INFO] Resumen guardado en: {summary_path}")

    return master_path, summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Consolida CSV procesados en el dataset maestro historico."
    )
    parser.add_argument(
        "--processed-file",
        type=Path,
        default=None,
        help="CSV procesado especifico a consolidar.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Consolida todos los licitaciones_processed_*.csv disponibles.",
    )
    args = parser.parse_args()

    if args.processed_file:
        processed_files = [args.processed_file]
    else:
        processed_files = find_processed_files(latest_only=not args.all)

    if not processed_files:
        raise FileNotFoundError(f"No se encontraron CSV procesados en: {PROCESSED_DIR}")

    print("\n[INFO] Iniciando append master...")
    print(f"[INFO] Archivos processed a consolidar: {len(processed_files)}")

    append_processed_files(processed_files)


if __name__ == "__main__":
    main()
