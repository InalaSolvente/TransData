from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MASTER_DIR = DATA_DIR / "master"
AUDIT_DIR = DATA_DIR / "processed" / "transport" / "audit"

TRANSPORT_MASTER_PATH = MASTER_DIR / "licitaciones_transport_master.csv"
TRANSPORT_MASTER_CORE_PATH = MASTER_DIR / "licitaciones_transport_master_core.csv"

DEFAULT_MANUAL_REVIEW_CSV = AUDIT_DIR / "transport_review_queue_reviewed_transdata_20260508.csv"
DEFAULT_MANUAL_REVIEW_SUMMARY = AUDIT_DIR / "transport_review_queue_reviewed_transdata_20260508_summary.json"

EXPLICIT_EXCLUDED_CODES = {
    "1049-58-CO25",
    "1049-59-CO25",
    "1049-40-LE25",
    "1049-41-LE25",
    "5061-162-L122",
    "2790-144-LQ22",
    "5061-92-L122",
}

EXPLICIT_MANUAL_REVIEW_CODES = {
    "1195104-26-LR24",
    "1195104-3-LR24",
}

REVIEW_MIN_COLUMNS = [
    "codigo_licitacion",
    "revision_decision_transdata",
    "revision_incluir_master_core",
    "revision_prioridad_negocio",
    "revision_confianza",
    "revision_segmento_validado",
    "revision_motivo",
    "revision_importancia",
    "revision_accion_recomendada",
]


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def env_str(name: str, default: str) -> str:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return value if value else default


def resolve_repo_path(path_like: Optional[Path | str]) -> Optional[Path]:
    if path_like is None:
        return None
    path = Path(path_like)
    if path.is_absolute():
        return path
    return ROOT / path


def now_str() -> str:
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_text(value) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_code(value) -> Optional[str]:
    if pd.isna(value):
        return None
    code = str(value).strip()
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
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "si", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return default


def ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df


def build_text_blob(row: pd.Series) -> str:
    parts = [
        row.get("nombre_licitacion"),
        row.get("descripcion"),
        row.get("detalle_descripcion"),
        row.get("transport_domain_context_hits"),
        row.get("transport_activity_context_hits"),
        row.get("transport_positive_hits"),
        row.get("transport_exclusion_hits"),
    ]
    return normalize_text(" ".join(str(part) for part in parts if part is not None and not pd.isna(part)))


def text_has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def load_manual_review_file(path: Optional[Path] = None) -> pd.DataFrame:
    manual_path = resolve_repo_path(
        path or env_str("MP_TRANSPORT_MANUAL_REVIEW_FILE", str(DEFAULT_MANUAL_REVIEW_CSV))
    )
    if not manual_path.exists():
        return pd.DataFrame(columns=REVIEW_MIN_COLUMNS)

    df = pd.read_csv(manual_path, encoding="utf-8-sig")
    df = ensure_columns(df, REVIEW_MIN_COLUMNS)
    df["codigo_licitacion"] = df["codigo_licitacion"].apply(normalize_code)
    df = df[df["codigo_licitacion"].notna()].copy()
    df = df.drop_duplicates(subset=["codigo_licitacion"], keep="last")

    if "revision_decision_transdata" in df.columns:
        df["revision_decision_transdata"] = (
            df["revision_decision_transdata"].fillna("").astype(str).str.strip().str.upper()
        )
    if "revision_incluir_master_core" in df.columns:
        df["revision_incluir_master_core"] = df["revision_incluir_master_core"].apply(coerce_bool)

    return df


def copy_manual_review_inputs(
    manual_review_path: Optional[Path],
    manual_review_summary_path: Optional[Path],
) -> dict[str, Optional[str]]:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    copied = {"manual_review_csv": None, "manual_review_summary_json": None}

    if manual_review_path and manual_review_path.exists():
        target = AUDIT_DIR / manual_review_path.name
        if manual_review_path.resolve() != target.resolve():
            shutil.copy2(manual_review_path, target)
        copied["manual_review_csv"] = str(target)

    if manual_review_summary_path and manual_review_summary_path.exists():
        target = AUDIT_DIR / manual_review_summary_path.name
        if manual_review_summary_path.resolve() != target.resolve():
            shutil.copy2(manual_review_summary_path, target)
        copied["manual_review_summary_json"] = str(target)

    return copied


def derive_auto_flags(row: pd.Series) -> dict[str, object]:
    text = build_text_blob(row)
    text_compact = text.replace("-", " ")
    es_transporte = coerce_bool(row.get("es_transporte"), default=False)

    non_land_patterns = [
        r"\blancha menor\b",
        r"\blancha\b",
        r"\bmaritim[oa]\b",
        r"\bbarcaza\b",
        r"\bembarcaci[oó]n\b",
        r"\baere[oa]\b",
        r"\bavion\b",
    ]
    mixed_bundle_patterns = [
        r"\balimentaci[oó]n\b",
        r"\bentradas?\b",
        r"\bhospedaje\b",
        r"\btickets?\b",
        r"\binsumos?\b",
        r"\bequipos?\b",
        r"\bayudas? sociales?\b",
        r"\bbarcaza\b",
    ]
    asset_purchase_patterns = [
        r"\badquisici[oó]n\b",
        r"\bcompra\b",
        r"\badquirir\b",
        r"\bsuministro\b",
    ]
    asset_subject_patterns = [
        r"\bambulancia\b",
        r"\bvehicul(?:o|os)\b",
    ]
    passenger_health_signals = [
        r"\bpacientes?\b",
        r"\bfuncionarios?\b",
        r"\busuarios?\b",
        r"\bvisitas? domiciliarias?\b",
        r"\batenci[oó]n domiciliaria\b",
        r"\btraslado de personas?\b",
        r"\btraslado de pasajeros?\b",
    ]
    medication_logistics_patterns = [
        r"\bentrega de medicamentos\b",
        r"\bmedicamentos a domicilio\b",
        r"\bfarmacia municipal\b",
    ]
    multimodal_patterns = [
        r"\bterrestre\b.*\b(maritim[oa]|aere[oa]|barcaza|lancha)\b",
        r"\b(maritim[oa]|aere[oa]|barcaza|lancha)\b.*\bterrestre\b",
        r"\bsermig\b",
    ]

    flag_non_land_mode = text_has_any(text_compact, non_land_patterns)
    flag_mixed_bundle = text_has_any(text_compact, mixed_bundle_patterns)
    flag_asset_purchase = (
        text_has_any(text_compact, asset_purchase_patterns)
        and text_has_any(text_compact, asset_subject_patterns)
        and not text_has_any(text_compact, [r"\bservicio de transporte\b", r"\bchofer\b", r"\bconductor\b"])
    )
    flag_logistics_not_passenger = (
        text_has_any(text_compact, medication_logistics_patterns)
        and not text_has_any(text_compact, passenger_health_signals)
    )
    flag_multimodal_review = text_has_any(text_compact, multimodal_patterns) or (
        flag_non_land_mode and es_transporte and "mixed_mode_review" in str(row.get("transport_review_flag", ""))
    )

    domain_hits = normalize_text(str(row.get("transport_domain_context_hits", "")))
    activity_hits = normalize_text(str(row.get("transport_activity_context_hits", "")))
    flag_health_transport = any(
        token in domain_hits or token in activity_hits
        for token in [
            "dom_aps",
            "dom_centros_salud",
            "dom_salud_ocupacional",
            "dom_cuidados_paliativos",
            "dom_farmacia",
            "ctx_atencion_domiciliaria",
            "ctx_visitas_domiciliarias",
        ]
    )
    flag_education_transport = any(
        token in domain_hits or token in activity_hits
        for token in [
            "dom_slep",
            "dom_escuela",
            "dom_liceo",
            "dom_establecimientos_educacionales",
            "dom_jardin_infantil",
            "dom_ceci",
            "ctx_salidas_pedagogicas",
            "ctx_salidas_extraescolares",
            "ctx_salidas_extracurriculares",
            "ctx_viajes_educativos",
            "ctx_gira_estudio",
        ]
    )
    flag_social_transport = any(
        token in domain_hits
        for token in [
            "dom_dideco",
            "dom_prlac",
            "dom_red_cuidados",
            "dom_adulto_mayor",
            "dom_discapacidad",
            "dom_chile_crece_contigo",
            "dom_ninez",
            "dom_sename",
            "dom_deudos",
        ]
    )

    return {
        "flag_mixed_bundle": bool(flag_mixed_bundle),
        "flag_non_land_mode": bool(flag_non_land_mode),
        "flag_asset_purchase": bool(flag_asset_purchase),
        "flag_logistics_not_passenger": bool(flag_logistics_not_passenger),
        "flag_multimodal_review": bool(flag_multimodal_review),
        "flag_health_transport": bool(flag_health_transport),
        "flag_education_transport": bool(flag_education_transport),
        "flag_social_transport": bool(flag_social_transport),
    }


def derive_auto_decision(row: pd.Series) -> dict[str, object]:
    code = normalize_code(row.get("codigo_licitacion"))
    flags = derive_auto_flags(row)
    es_transporte = coerce_bool(row.get("es_transporte"), default=False)

    if code in EXPLICIT_EXCLUDED_CODES:
        decision = "EXCLUIR"
        include = False
    elif code in EXPLICIT_MANUAL_REVIEW_CODES:
        decision = "REVISAR_MANUAL"
        include = False
        flags["flag_multimodal_review"] = True
    elif flags["flag_asset_purchase"] or flags["flag_logistics_not_passenger"]:
        decision = "EXCLUIR"
        include = False
    elif flags["flag_non_land_mode"] and flags["flag_multimodal_review"]:
        decision = "REVISAR_MANUAL"
        include = False
    elif flags["flag_non_land_mode"]:
        decision = "EXCLUIR"
        include = False
    elif flags["flag_mixed_bundle"] and es_transporte:
        decision = "INCLUIR_PARCIAL"
        include = True
    elif es_transporte or flags["flag_health_transport"] or flags["flag_education_transport"] or flags["flag_social_transport"]:
        decision = "INCLUIR"
        include = True
    else:
        decision = "EXCLUIR"
        include = False

    flags["flag_clean_transport_amount"] = bool(include and decision != "INCLUIR_PARCIAL")
    return {
        "auto_revision_decision_transdata": decision,
        "auto_revision_incluir_master_core": include,
        **flags,
    }


def apply_manual_review_to_dataframe(
    df: pd.DataFrame,
    manual_review_df: Optional[pd.DataFrame] = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    df = df.copy()
    df["codigo_licitacion"] = df["codigo_licitacion"].apply(normalize_code)
    df = df[df["codigo_licitacion"].notna()].copy()

    if manual_review_df is None:
        manual_review_df = load_manual_review_file()
    else:
        manual_review_df = ensure_columns(manual_review_df, REVIEW_MIN_COLUMNS)
        manual_review_df = manual_review_df.copy()
        manual_review_df["codigo_licitacion"] = manual_review_df["codigo_licitacion"].apply(normalize_code)
        manual_review_df = manual_review_df[manual_review_df["codigo_licitacion"].notna()].copy()
        manual_review_df = manual_review_df.drop_duplicates(subset=["codigo_licitacion"], keep="last")

    auto_flags = df.apply(lambda row: derive_auto_decision(row), axis=1, result_type="expand")
    df = pd.concat([df.reset_index(drop=True), auto_flags.reset_index(drop=True)], axis=1)

    review_lookup = manual_review_df.set_index("codigo_licitacion") if not manual_review_df.empty else pd.DataFrame().set_index(pd.Index([]))

    df["revision_manual_match"] = df["codigo_licitacion"].isin(set(review_lookup.index))
    for column in REVIEW_MIN_COLUMNS:
        if column == "codigo_licitacion":
            continue
        df[column] = df["codigo_licitacion"].map(review_lookup[column]) if column in review_lookup.columns else pd.NA

    df["revision_decision_transdata"] = df["revision_decision_transdata"].fillna("")
    df["revision_decision_transdata"] = df["revision_decision_transdata"].astype(str).str.strip().str.upper()
    df.loc[df["revision_decision_transdata"].eq(""), "revision_decision_transdata"] = df["auto_revision_decision_transdata"]

    reviewed_include = df["revision_incluir_master_core"].apply(lambda value: coerce_bool(value, default=False))
    auto_include = df["auto_revision_incluir_master_core"].apply(lambda value: coerce_bool(value, default=False))
    df["revision_incluir_master_core"] = auto_include
    df.loc[df["revision_manual_match"], "revision_incluir_master_core"] = reviewed_include[df["revision_manual_match"]]

    df["revision_decision_source"] = "auto_rule"
    df.loc[df["revision_manual_match"], "revision_decision_source"] = "manual_review"

    df.loc[df["revision_decision_transdata"].eq("INCLUIR_PARCIAL"), "flag_mixed_bundle"] = True
    df["flag_clean_transport_amount"] = ~df["revision_decision_transdata"].eq("INCLUIR_PARCIAL")
    df.loc[~df["revision_incluir_master_core"], "flag_clean_transport_amount"] = False

    df.loc[df["revision_decision_transdata"].eq("REVISAR_MANUAL"), "flag_multimodal_review"] = True
    df["revision_pending_manual"] = df["revision_decision_transdata"].eq("REVISAR_MANUAL")

    summary = {
        "input_rows": int(len(df)),
        "review_rows_loaded": int(len(manual_review_df)),
        "matched_manual_review_rows": int(df["revision_manual_match"].sum()),
        "decision_counts": df["revision_decision_transdata"].value_counts(dropna=False).to_dict(),
        "segment_counts": df["revision_segmento_validado"].fillna("").replace("", pd.NA).dropna().value_counts().to_dict(),
        "priority_counts": df["revision_prioridad_negocio"].fillna("").replace("", pd.NA).dropna().value_counts().to_dict(),
        "included_core_rows": int(df["revision_incluir_master_core"].sum()),
        "partial_include_rows": int(df["revision_decision_transdata"].eq("INCLUIR_PARCIAL").sum()),
        "excluded_rows": int(df["revision_decision_transdata"].eq("EXCLUIR").sum()),
        "manual_review_rows": int(df["revision_decision_transdata"].eq("REVISAR_MANUAL").sum()),
    }
    return df, summary


def write_manual_review_outputs(
    df_applied: pd.DataFrame,
    summary: dict[str, object],
    output_dir: Path = AUDIT_DIR,
    core_master_path: Path = TRANSPORT_MASTER_CORE_PATH,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    full_path = output_dir / f"transport_master_with_manual_review_{timestamp}.csv"
    summary_path = output_dir / f"transport_manual_review_applied_summary_{timestamp}.json"
    excluded_path = output_dir / f"transport_excluded_by_manual_review_{timestamp}.csv"
    partial_path = output_dir / f"transport_partial_includes_{timestamp}.csv"
    pending_path = output_dir / f"transport_manual_review_pending_{timestamp}.csv"

    df_applied.to_csv(full_path, index=False, encoding="utf-8-sig")
    df_applied[df_applied["revision_decision_transdata"].eq("EXCLUIR")].to_csv(
        excluded_path, index=False, encoding="utf-8-sig"
    )
    df_applied[df_applied["revision_decision_transdata"].eq("INCLUIR_PARCIAL")].to_csv(
        partial_path, index=False, encoding="utf-8-sig"
    )
    df_applied[df_applied["revision_decision_transdata"].eq("REVISAR_MANUAL")].to_csv(
        pending_path, index=False, encoding="utf-8-sig"
    )

    core_df = df_applied[df_applied["revision_incluir_master_core"]].copy()
    core_df.to_csv(core_master_path, index=False, encoding="utf-8-sig")

    full_summary = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "core_master_path": str(core_master_path),
        },
        **summary,
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(full_summary, handle, ensure_ascii=False, indent=2)

    return {
        "core_master_path": str(core_master_path),
        "full_path": str(full_path),
        "summary_path": str(summary_path),
        "excluded_path": str(excluded_path),
        "partial_path": str(partial_path),
        "pending_path": str(pending_path),
    }


def rebuild_transport_master_core(
    master_path: Path = TRANSPORT_MASTER_PATH,
    manual_review_path: Optional[Path] = None,
    manual_review_summary_path: Optional[Path] = None,
    output_dir: Path = AUDIT_DIR,
    core_master_path: Path = TRANSPORT_MASTER_CORE_PATH,
) -> dict[str, object]:
    if not master_path.exists():
        raise FileNotFoundError(f"No existe transport master: {master_path}")

    manual_review_path = resolve_repo_path(
        manual_review_path or env_str("MP_TRANSPORT_MANUAL_REVIEW_FILE", str(DEFAULT_MANUAL_REVIEW_CSV))
    )
    manual_review_summary_path = resolve_repo_path(
        manual_review_summary_path or env_str("MP_TRANSPORT_MANUAL_REVIEW_SUMMARY_FILE", str(DEFAULT_MANUAL_REVIEW_SUMMARY))
    )

    copied_inputs = copy_manual_review_inputs(
        manual_review_path if manual_review_path.exists() else None,
        manual_review_summary_path if manual_review_summary_path.exists() else None,
    )

    df_master = pd.read_csv(master_path, encoding="utf-8-sig")
    manual_review_df = load_manual_review_file(manual_review_path)
    if manual_review_df.empty:
        print(
            "[WARN] No se encontro CSV de revision manual o no tenia filas validas. "
            "Se aplicaran solo reglas automaticas y overrides explicitos por codigo."
        )
    df_applied, summary = apply_manual_review_to_dataframe(df_master, manual_review_df)
    outputs = write_manual_review_outputs(
        df_applied=df_applied,
        summary=summary,
        output_dir=output_dir,
        core_master_path=core_master_path,
    )

    result = {
        "master_path": str(master_path),
        "manual_review_path": str(manual_review_path) if manual_review_path.exists() else None,
        "manual_review_summary_path": (
            str(manual_review_summary_path) if manual_review_summary_path.exists() else None
        ),
        **copied_inputs,
        **summary,
        **outputs,
    }

    print("[OK] Revision manual aplicada al transport master.")
    print(f"[INFO] Filas de entrada: {result['input_rows']}")
    print(f"[INFO] Filas del review manual cargadas: {result['review_rows_loaded']}")
    print(f"[INFO] Filas matcheadas por codigo: {result['matched_manual_review_rows']}")
    print(f"[INFO] Filas incluidas en core: {result['included_core_rows']}")
    print(f"[INFO] Filas parciales: {result['partial_include_rows']}")
    print(f"[INFO] Filas excluidas: {result['excluded_rows']}")
    print(f"[INFO] Filas en revision manual: {result['manual_review_rows']}")
    print(f"[INFO] Core master: {result['core_master_path']}")
    print(f"[INFO] Resumen manual review: {result['summary_path']}")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Aplica revisión manual de transporte y reconstruye el master core."
    )
    parser.add_argument(
        "--master-path",
        type=Path,
        default=TRANSPORT_MASTER_PATH,
        help="Ruta del transport master amplio.",
    )
    parser.add_argument(
        "--manual-review-file",
        type=Path,
        default=None,
        help="CSV revisado manualmente.",
    )
    parser.add_argument(
        "--manual-review-summary-file",
        type=Path,
        default=None,
        help="JSON resumen del review manual.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=AUDIT_DIR,
        help="Directorio para salidas de auditoría.",
    )
    parser.add_argument(
        "--core-master-path",
        type=Path,
        default=TRANSPORT_MASTER_CORE_PATH,
        help="Ruta del master core reconstruido.",
    )
    args = parser.parse_args()

    rebuild_transport_master_core(
        master_path=args.master_path,
        manual_review_path=args.manual_review_file,
        manual_review_summary_path=args.manual_review_summary_file,
        output_dir=args.output_dir,
        core_master_path=args.core_master_path,
    )


if __name__ == "__main__":
    main()
