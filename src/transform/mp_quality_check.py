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
REPORTS_DIR = DATA_DIR / "reports" / "quality"

TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
DEFAULT_QUALITY_MASTER_PATH = TRANSPORT_MASTER_CORE_PATH


def load_transport_master(master_path: Path) -> pd.DataFrame:
    if not master_path.exists():
        raise FileNotFoundError(f"No existe transport master: {master_path}")
    return pd.read_csv(master_path, encoding="utf-8-sig")


def resolve_master_path(master_path: Path | None = None) -> Path:
    if master_path is not None:
        return master_path
    if DEFAULT_QUALITY_MASTER_PATH.exists():
        return DEFAULT_QUALITY_MASTER_PATH
    return TRANSPORT_MASTER_PATH


def normalize_bool_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna(False)
        .astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "si", "yes"})
    )


def normalize_text_series(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )


def parse_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def build_issue_record(issue_type: str, count: int, severity: str, description: str) -> Dict[str, object]:
    return {
        "issue_type": issue_type,
        "severity": severity,
        "count": int(count),
        "description": description,
    }


def collect_issues(df: pd.DataFrame) -> List[Dict[str, object]]:
    issues: List[Dict[str, object]] = []

    codigo_missing = normalize_text_series(df.get("codigo_licitacion", pd.Series([], dtype="object"))).eq("").sum()
    if codigo_missing:
        issues.append(build_issue_record("missing_codigo_licitacion", codigo_missing, "critical", "Filas sin codigo_licitacion."))

    duplicate_codes = (
        normalize_text_series(df.get("codigo_licitacion", pd.Series([], dtype="object")))
        .replace("", pd.NA)
        .dropna()
        .duplicated(keep=False)
        .sum()
    )
    if duplicate_codes:
        issues.append(build_issue_record("duplicate_codigo_licitacion", duplicate_codes, "critical", "Codigos duplicados en transport master."))

    nombre_missing = normalize_text_series(df.get("nombre_licitacion", pd.Series([], dtype="object"))).eq("").sum()
    if nombre_missing:
        issues.append(build_issue_record("missing_nombre_licitacion", nombre_missing, "warning", "Filas sin nombre_licitacion original."))

    buyer_missing = normalize_text_series(df.get("detalle_comprador_nombre", pd.Series([], dtype="object"))).eq("").sum()
    if buyer_missing:
        issues.append(build_issue_record("missing_detalle_comprador_nombre", buyer_missing, "warning", "Filas sin comprador enriquecido."))

    detail_status = normalize_text_series(df.get("detalle_status", pd.Series([], dtype="object"))).str.lower()
    detail_status_other = (~detail_status.isin({"", "success", "pending", "error"})).sum()
    if detail_status_other:
        issues.append(build_issue_record("unexpected_detalle_status", detail_status_other, "warning", "Valores no esperados en detalle_status."))

    codigo_estado = parse_numeric_series(df.get("detalle_codigo_estado", pd.Series([], dtype="object")))
    codigo_estado_missing = codigo_estado.isna().sum()
    if codigo_estado_missing:
        issues.append(build_issue_record("missing_detalle_codigo_estado", codigo_estado_missing, "warning", "Filas sin codigo de estado enriquecido."))

    adjudicada_mask = codigo_estado.eq(8) | normalize_text_series(df.get("detalle_estado", pd.Series([], dtype="object"))).str.lower().eq("adjudicada")
    adjudicacion_capturada = normalize_bool_series(df.get("adjudicacion_capturada", pd.Series([], dtype="object")))
    adjudicadas_sin_captura = (adjudicada_mask & ~adjudicacion_capturada).sum()
    if adjudicadas_sin_captura:
        issues.append(
            build_issue_record(
                "adjudicadas_sin_adjudicacion_capturada",
                adjudicadas_sin_captura,
                "warning",
                "Licitaciones adjudicadas que aun no tienen adjudicacion capturada en el master.",
            )
        )

    adjudicacion_fields = normalize_text_series(df.get("proveedor_adjudicado_nombre", pd.Series([], dtype="object"))).ne("")
    adjudicacion_inconsistente = (~adjudicada_mask & adjudicacion_fields).sum()
    if adjudicacion_inconsistente:
        issues.append(
            build_issue_record(
                "proveedor_adjudicado_en_no_adjudicadas",
                adjudicacion_inconsistente,
                "warning",
                "Filas con proveedor adjudicado informado pero sin estado adjudicada.",
            )
        )

    region_missing = normalize_text_series(df.get("detalle_comprador_region", pd.Series([], dtype="object"))).eq("").sum()
    if region_missing:
        issues.append(build_issue_record("missing_detalle_comprador_region", region_missing, "info", "Filas sin region enriquecida del comprador."))

    score_numeric = parse_numeric_series(df.get("transport_score", pd.Series([], dtype="object")))
    low_score_rows = score_numeric.lt(3).fillna(False).sum()
    if low_score_rows:
        issues.append(build_issue_record("transport_score_bajo", low_score_rows, "info", "Filas con score de transporte menor al umbral base 3."))

    return issues


def build_summary(df: pd.DataFrame, issues: List[Dict[str, object]]) -> Dict[str, object]:
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for issue in issues:
        severity = str(issue["severity"])
        severity_counts[severity] = severity_counts.get(severity, 0) + int(issue["count"])

    detail_status = normalize_text_series(df.get("detalle_status", pd.Series([], dtype="object"))).str.lower()
    estado_grupo = normalize_text_series(df.get("detalle_estado", pd.Series([], dtype="object"))).str.lower()

    return {
        "generated_at": datetime.now().isoformat(),
        "total_rows": int(len(df)),
        "unique_codigos": int(df["codigo_licitacion"].nunique()) if "codigo_licitacion" in df.columns else 0,
        "enriched_rows": int(normalize_bool_series(df.get("enriched", pd.Series([], dtype="object"))).sum()),
        "adjudicacion_capturada_rows": int(normalize_bool_series(df.get("adjudicacion_capturada", pd.Series([], dtype="object"))).sum()),
        "refresh_pending_rows": int(normalize_bool_series(df.get("requiere_refresh_adjudicacion", pd.Series([], dtype="object"))).sum()),
        "detail_status_counts": detail_status.value_counts(dropna=False).to_dict(),
        "detalle_estado_counts_top10": estado_grupo.value_counts(dropna=False).head(10).to_dict(),
        "issues_count": len(issues),
        "severity_counts": severity_counts,
    }


def write_outputs(summary: Dict[str, object], issues: List[Dict[str, object]], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_path = output_dir / f"transport_quality_summary_{timestamp}.json"
    issues_path = output_dir / f"transport_quality_issues_{timestamp}.csv"

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    pd.DataFrame(issues).to_csv(issues_path, index=False, encoding="utf-8-sig")
    return {"summary_path": summary_path, "issues_path": issues_path}


def run_quality_check(master_path: Path | None = None, output_dir: Path = REPORTS_DIR) -> Dict[str, object]:
    resolved_master_path = resolve_master_path(master_path)
    df = load_transport_master(resolved_master_path)
    issues = collect_issues(df)
    summary = build_summary(df, issues)
    outputs = write_outputs(summary, issues, output_dir)

    result = {
        "master_path": str(resolved_master_path),
        "output_dir": str(output_dir),
        **summary,
        **{key: str(value) for key, value in outputs.items()},
        "provisional_note": (
            "Este chequeo de calidad lee el transport master core cuando existe, "
            "con fallback al transport master amplio. Puede cambiar cuando el refresh "
            "empiece a corregir estados y adjudicaciones."
        ),
    }

    print("[OK] Quality check generado.")
    print(f"[INFO] Filas evaluadas: {result['total_rows']}")
    print(f"[INFO] Issues detectados: {result['issues_count']}")
    print(f"[INFO] Resumen quality: {result['summary_path']}")
    print(f"[INFO] Detalle issues: {result['issues_path']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Genera un chequeo de calidad del transport master."
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
        default=REPORTS_DIR,
        help="Directorio de salida para reportes de calidad.",
    )
    args = parser.parse_args()

    run_quality_check(master_path=args.master_path, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
