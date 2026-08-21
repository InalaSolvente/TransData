import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from mp_enrich_details import summarize_enrich_backlog


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MASTER_DIR = DATA_DIR / "master"
PIPELINE_DIR = PROCESSED_DIR / "pipeline"
REPORTS_DIR = DATA_DIR / "reports"
ANALYTICS_DIR = DATA_DIR / "analytics"
QUALITY_DIR = REPORTS_DIR / "quality"
SERVING_DIR = DATA_DIR / "serving"
TRANSPORT_AUDIT_DIR = PROCESSED_DIR / "transport" / "audit"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def try_load_json(path: Path):
    try:
        return load_json(path)
    except Exception:
        return None


def compact_summary_payload(payload):
    if not isinstance(payload, dict):
        return payload

    compacted = {}
    for key in ["metadata", "results", "steps"]:
        if key in payload:
            compacted[key] = payload[key]

    return compacted if compacted else payload


def find_latest_file(directory: Path, pattern: str):
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        return None
    return files[-1]


def parse_mp_date(value):
    try:
        return datetime.strptime(str(value), "%d%m%Y").date()
    except Exception:
        return None


def summarize_raw_layer():
    raw_files = sorted(RAW_DIR.glob("mp_raw_*.json"), key=lambda p: p.stat().st_mtime)
    batch_summary_files = sorted(RAW_DIR.glob("mp_batch_summary_*.json"), key=lambda p: p.stat().st_mtime)

    success_dates = set()
    failed_dates = set()
    raw_with_records = 0
    raw_without_records = 0
    raw_all_failed = 0
    total_records_found = 0

    for raw_path in raw_files:
        payload = try_load_json(raw_path)
        if not payload:
            continue

        metadata = payload.get("metadata", {})
        failed_queries = payload.get("failed_queries", [])
        results = payload.get("results", [])

        raw_records = int(metadata.get("total_records_found") or 0)
        total_records_found += raw_records

        if results and raw_records > 0:
            raw_with_records += 1
        elif results:
            raw_without_records += 1
        else:
            raw_all_failed += 1

        for result in results:
            fecha = result.get("fecha_consulta")
            if fecha:
                success_dates.add(fecha)

        for failed in failed_queries:
            fecha = failed.get("fecha_consulta")
            if fecha:
                failed_dates.add(fecha)

    success_date_objs = sorted(d for d in (parse_mp_date(x) for x in success_dates) if d is not None)
    date_range_start = success_date_objs[0].isoformat() if success_date_objs else None
    date_range_end = success_date_objs[-1].isoformat() if success_date_objs else None

    latest_batch_summary = find_latest_file(RAW_DIR, "mp_batch_summary_*.json")
    latest_batch_payload = try_load_json(latest_batch_summary) if latest_batch_summary else None

    return {
        "raw_files": len(raw_files),
        "batch_summary_files": len(batch_summary_files),
        "raw_with_records": raw_with_records,
        "raw_without_records": raw_without_records,
        "raw_all_failed": raw_all_failed,
        "success_dates_count": len(success_dates),
        "failed_dates_count": len(failed_dates),
        "success_date_range_start": date_range_start,
        "success_date_range_end": date_range_end,
        "total_records_found_raw": total_records_found,
        "latest_batch_summary_path": str(latest_batch_summary) if latest_batch_summary else None,
        "latest_batch_summary": latest_batch_payload.get("results") if latest_batch_payload else None,
    }


def summarize_processed_layer():
    processed_files = sorted(PROCESSED_DIR.glob("licitaciones_processed_*.csv"), key=lambda p: p.stat().st_mtime)
    latest_transform_summary = find_latest_file(PROCESSED_DIR, "mp_transform_summary_*.json")
    latest_runner_summary = find_latest_file(PIPELINE_DIR, "mp_transform_runner_summary_*.json")

    total_processed_rows = 0
    for path in processed_files:
        try:
            df = pd.read_csv(path, encoding="utf-8-sig", usecols=["codigo_licitacion"])
            total_processed_rows += len(df)
        except Exception:
            continue

    return {
        "processed_files": len(processed_files),
        "total_processed_rows": total_processed_rows,
        "latest_processed_file": str(processed_files[-1]) if processed_files else None,
        "latest_transform_summary_path": str(latest_transform_summary) if latest_transform_summary else None,
        "latest_transform_summary": (
            compact_summary_payload(try_load_json(latest_transform_summary))
            if latest_transform_summary else None
        ),
        "latest_runner_summary_path": str(latest_runner_summary) if latest_runner_summary else None,
        "latest_runner_summary": (
            compact_summary_payload(try_load_json(latest_runner_summary))
            if latest_runner_summary else None
        ),
    }


def coerce_bool_series(series: pd.Series) -> pd.Series:
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"true", "1", "si", "yes"})


def coerce_int_series(series: pd.Series, default: int = 0) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce").fillna(default)
    return numeric.astype(int)


def summarize_master_layer():
    general_master = MASTER_DIR / "licitaciones_master.csv"
    transport_master = MASTER_DIR / "licitaciones_transport_master.csv"
    transport_core_master = MASTER_DIR / "licitaciones_transport_master_core.csv"
    transport_refresh_history = DATA_DIR / "history" / "licitaciones_transport_status_history.csv"

    general_rows = None
    transport_rows = None
    transport_enriched = None
    transport_pending = None
    transport_error_status = None
    transport_retry_needed = None
    avg_attempts = None
    enrich_backlog = None
    refresh_history_rows = None
    latest_refresh_at = None
    transport_adjudicacion_capturada_rows = None
    transport_refresh_pending_award_rows = None
    transport_supplier_name_rows = None
    transport_supplier_rut_rows = None
    transport_refresh_success_rows = None
    transport_refresh_error_rows = None
    transport_core_master_rows = None

    if general_master.exists():
        try:
            general_rows = len(pd.read_csv(general_master, encoding="utf-8-sig", usecols=["codigo_licitacion"]))
        except Exception:
            general_rows = None

    if transport_master.exists():
        df_transport = pd.read_csv(transport_master, encoding="utf-8-sig")
        transport_rows = len(df_transport)
        enrich_backlog = summarize_enrich_backlog(df_transport)

        if "enriched" in df_transport.columns:
            enriched_series = coerce_bool_series(df_transport["enriched"].fillna(False))
            transport_enriched = int(enriched_series.sum())
            transport_pending = int((~enriched_series).sum())

        if "detalle_status" in df_transport.columns:
            status_series = df_transport["detalle_status"].fillna("pending").astype(str).str.lower()
            transport_error_status = int((status_series == "error").sum())

        if "detalle_needs_retry" in df_transport.columns:
            retry_series = coerce_bool_series(df_transport["detalle_needs_retry"].fillna("").astype(str))
            transport_retry_needed = int(retry_series.sum())

        if "detalle_attempts_total" in df_transport.columns:
            avg_attempts = float(coerce_int_series(df_transport["detalle_attempts_total"]).mean())

        if "adjudicacion_capturada" in df_transport.columns:
            captured_series = coerce_bool_series(df_transport["adjudicacion_capturada"].fillna(False))
            transport_adjudicacion_capturada_rows = int(captured_series.sum())

        if "requiere_refresh_adjudicacion" in df_transport.columns:
            refresh_pending_series = coerce_bool_series(df_transport["requiere_refresh_adjudicacion"].fillna(False))
            transport_refresh_pending_award_rows = int(refresh_pending_series.sum())

        if "proveedor_adjudicado_nombre" in df_transport.columns:
            supplier_name_series = (
                df_transport["proveedor_adjudicado_nombre"]
                .fillna("")
                .astype(str)
                .str.strip()
            )
            transport_supplier_name_rows = int(supplier_name_series.ne("").sum())

        if "proveedor_adjudicado_rut" in df_transport.columns:
            supplier_rut_series = (
                df_transport["proveedor_adjudicado_rut"]
                .fillna("")
                .astype(str)
                .str.strip()
            )
            transport_supplier_rut_rows = int(supplier_rut_series.ne("").sum())

        if "refresh_status" in df_transport.columns:
            refresh_status_series = df_transport["refresh_status"].fillna("").astype(str).str.strip().str.lower()
            transport_refresh_success_rows = int((refresh_status_series == "success").sum())
            transport_refresh_error_rows = int((refresh_status_series == "error").sum())

    if transport_core_master.exists():
        try:
            transport_core_master_rows = len(
                pd.read_csv(transport_core_master, encoding="utf-8-sig", usecols=["codigo_licitacion"])
            )
        except Exception:
            transport_core_master_rows = None
    latest_enrich_summary = find_latest_file(MASTER_DIR, "mp_enrich_transport_summary_*.json")
    latest_refresh_summary = find_latest_file(MASTER_DIR, "mp_refresh_summary_*.json")

    if transport_refresh_history.exists():
        try:
            df_history = pd.read_csv(transport_refresh_history, encoding="utf-8-sig")
            refresh_history_rows = len(df_history)
            if "fecha_refresh" in df_history.columns and not df_history.empty:
                latest_refresh_at = str(df_history["fecha_refresh"].dropna().iloc[-1])
        except Exception:
            refresh_history_rows = None

    return {
        "general_master_path": str(general_master) if general_master.exists() else None,
        "general_master_rows": general_rows,
        "transport_master_path": str(transport_master) if transport_master.exists() else None,
        "transport_master_rows": transport_rows,
        "transport_core_master_path": str(transport_core_master) if transport_core_master.exists() else None,
        "transport_core_master_rows": transport_core_master_rows,
        "transport_enriched_rows": transport_enriched,
        "transport_pending_enrich_rows": transport_pending,
        "transport_error_status_rows": transport_error_status,
        "transport_retry_needed_rows": transport_retry_needed,
        "transport_average_attempts": avg_attempts,
        "transport_adjudicacion_capturada_rows": transport_adjudicacion_capturada_rows,
        "transport_refresh_pending_award_rows": transport_refresh_pending_award_rows,
        "transport_supplier_name_rows": transport_supplier_name_rows,
        "transport_supplier_rut_rows": transport_supplier_rut_rows,
        "transport_refresh_success_rows": transport_refresh_success_rows,
        "transport_refresh_error_rows": transport_refresh_error_rows,
        "transport_enrich_backlog": enrich_backlog,
        "transport_refresh_history_path": str(transport_refresh_history) if transport_refresh_history.exists() else None,
        "transport_refresh_history_rows": refresh_history_rows,
        "transport_latest_refresh_at": latest_refresh_at,
        "latest_enrich_summary_path": str(latest_enrich_summary) if latest_enrich_summary else None,
        "latest_enrich_summary": (
            compact_summary_payload(try_load_json(latest_enrich_summary))
            if latest_enrich_summary else None
        ),
        "latest_refresh_summary_path": str(latest_refresh_summary) if latest_refresh_summary else None,
        "latest_refresh_summary": (
            compact_summary_payload(try_load_json(latest_refresh_summary))
            if latest_refresh_summary else None
        ),
    }


def summarize_derived_layer():
    latest_analytics_summary = find_latest_file(ANALYTICS_DIR, "transport_analytics_summary_*.json")
    latest_quality_summary = find_latest_file(QUALITY_DIR, "transport_quality_summary_*.json")
    latest_serving_manifest = find_latest_file(SERVING_DIR, "transport_dataset_manifest_*.json")
    latest_serving_dataset = SERVING_DIR / "transport_dataset_latest.csv"
    latest_transport_rule_audit = find_latest_file(TRANSPORT_AUDIT_DIR, "transport_rule_audit_summary_*.json")
    latest_transport_rule_review = find_latest_file(TRANSPORT_AUDIT_DIR, "transport_rule_review_summary_*.json")
    latest_transport_review_queue = find_latest_file(TRANSPORT_AUDIT_DIR, "transport_review_queue_summary_*.json")

    analytics_rows = None
    serving_rows = None
    quality_issues_count = None
    transport_rule_removed_rows = None
    transport_rule_review_rows = None
    transport_rule_review_group_counts = None

    if latest_analytics_summary:
        payload = try_load_json(latest_analytics_summary)
        if isinstance(payload, dict):
            analytics_rows = payload.get("rows")

    if latest_quality_summary:
        payload = try_load_json(latest_quality_summary)
        if isinstance(payload, dict):
            quality_issues_count = payload.get("issues_count")

    if latest_serving_dataset.exists():
        try:
            serving_rows = len(pd.read_csv(latest_serving_dataset, encoding="utf-8-sig", usecols=["codigo_licitacion"]))
        except Exception:
            serving_rows = None

    if latest_transport_rule_audit:
        payload = try_load_json(latest_transport_rule_audit)
        if isinstance(payload, dict):
            transport_rule_removed_rows = payload.get("results", {}).get("removed_rows")

    if latest_transport_review_queue:
        payload = try_load_json(latest_transport_review_queue)
        if isinstance(payload, dict):
            transport_rule_review_rows = payload.get("results", {}).get("review_rows")
            transport_rule_review_group_counts = payload.get("results", {}).get("group_counts")

    return {
        "analytics_dir": str(ANALYTICS_DIR) if ANALYTICS_DIR.exists() else None,
        "latest_analytics_summary_path": str(latest_analytics_summary) if latest_analytics_summary else None,
        "latest_analytics_summary": (
            compact_summary_payload(try_load_json(latest_analytics_summary))
            if latest_analytics_summary else None
        ),
        "analytics_rows": analytics_rows,
        "quality_dir": str(QUALITY_DIR) if QUALITY_DIR.exists() else None,
        "latest_quality_summary_path": str(latest_quality_summary) if latest_quality_summary else None,
        "latest_quality_summary": (
            compact_summary_payload(try_load_json(latest_quality_summary))
            if latest_quality_summary else None
        ),
        "quality_issues_count": quality_issues_count,
        "serving_dir": str(SERVING_DIR) if SERVING_DIR.exists() else None,
        "latest_serving_manifest_path": str(latest_serving_manifest) if latest_serving_manifest else None,
        "latest_serving_manifest": (
            compact_summary_payload(try_load_json(latest_serving_manifest))
            if latest_serving_manifest else None
        ),
        "latest_serving_dataset_path": str(latest_serving_dataset) if latest_serving_dataset.exists() else None,
        "serving_rows": serving_rows,
        "transport_audit_dir": str(TRANSPORT_AUDIT_DIR) if TRANSPORT_AUDIT_DIR.exists() else None,
        "latest_transport_rule_audit_path": str(latest_transport_rule_audit) if latest_transport_rule_audit else None,
        "latest_transport_rule_audit": (
            compact_summary_payload(try_load_json(latest_transport_rule_audit))
            if latest_transport_rule_audit else None
        ),
        "transport_rule_removed_rows": transport_rule_removed_rows,
        "latest_transport_rule_review_path": str(latest_transport_rule_review) if latest_transport_rule_review else None,
        "latest_transport_rule_review": (
            compact_summary_payload(try_load_json(latest_transport_rule_review))
            if latest_transport_rule_review else None
        ),
        "latest_transport_review_queue_path": str(latest_transport_review_queue) if latest_transport_review_queue else None,
        "latest_transport_review_queue": (
            compact_summary_payload(try_load_json(latest_transport_review_queue))
            if latest_transport_review_queue else None
        ),
        "transport_rule_review_rows": transport_rule_review_rows,
        "transport_rule_review_group_counts": transport_rule_review_group_counts,
    }


def build_health_report():
    return {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "project_root": str(ROOT),
        },
        "raw_layer": summarize_raw_layer(),
        "processed_layer": summarize_processed_layer(),
        "master_layer": summarize_master_layer(),
        "derived_layer": summarize_derived_layer(),
    }


def write_health_report(report):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"mp_pipeline_health_{timestamp}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return path


def print_health_report(report, report_path):
    raw = report["raw_layer"]
    processed = report["processed_layer"]
    master = report["master_layer"]
    derived = report["derived_layer"]

    print("[INFO] Pipeline health report generado")
    print(f"[INFO] Reporte: {report_path}")
    print(f"[INFO] Raw files: {raw['raw_files']}")
    print(f"[INFO] Fechas con éxito en ingest: {raw['success_dates_count']}")
    print(f"[INFO] Rango cubierto: {raw['success_date_range_start']} -> {raw['success_date_range_end']}")
    print(f"[INFO] Processed files: {processed['processed_files']}")
    print(f"[INFO] Filas acumuladas en processed: {processed['total_processed_rows']}")
    print(f"[INFO] General master rows: {master['general_master_rows']}")
    print(f"[INFO] Transport master rows: {master['transport_master_rows']}")
    print(f"[INFO] Transport enriched rows: {master['transport_enriched_rows']}")
    print(f"[INFO] Transport pending enrich rows: {master['transport_pending_enrich_rows']}")
    print(f"[INFO] Transport retry needed rows: {master['transport_retry_needed_rows']}")
    print(f"[INFO] Transport refresh history rows: {master['transport_refresh_history_rows']}")
    print(f"[INFO] Transport adjudicaciones capturadas: {master['transport_adjudicacion_capturada_rows']}")
    print(f"[INFO] Transport pendientes de adjudicacion: {master['transport_refresh_pending_award_rows']}")
    print(f"[INFO] Transport refresh success rows: {master['transport_refresh_success_rows']}")
    print(f"[INFO] Transport refresh error rows: {master['transport_refresh_error_rows']}")
    print(f"[INFO] Analytics rows: {derived['analytics_rows']}")
    print(f"[INFO] Quality issues count: {derived['quality_issues_count']}")
    print(f"[INFO] Serving rows: {derived['serving_rows']}")
    print(f"[INFO] Transport rule removed rows: {derived['transport_rule_removed_rows']}")
    print(f"[INFO] Transport review pending rows: {derived['transport_rule_review_rows']}")


def main():
    parser = argparse.ArgumentParser(description="Genera reporte de salud y cobertura del pipeline.")
    parser.parse_args()

    report = build_health_report()
    report_path = write_health_report(report)
    print_health_report(report, report_path)


if __name__ == "__main__":
    main()
