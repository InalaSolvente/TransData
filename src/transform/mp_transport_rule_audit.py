import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from mp_transport_filter import classify_dataframe


ROOT = Path(__file__).resolve().parents[2]
MASTER_PATH = ROOT / "data" / "master" / "licitaciones_transport_master.csv"
AUDIT_DIR = ROOT / "data" / "processed" / "transport" / "audit"


def load_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def drop_existing_transport_columns(df):
    columns_to_drop = [
        column
        for column in df.columns
        if column == "es_transporte" or column.startswith("transport_")
    ]
    if not columns_to_drop:
        return df.copy()
    return df.drop(columns=columns_to_drop).copy()


def write_audit_outputs(summary, removed_df, reviewed_df, output_dir=AUDIT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    summary_path = output_dir / f"transport_rule_audit_summary_{timestamp}.json"
    removed_path = output_dir / f"transport_rule_audit_removed_{timestamp}.csv"
    review_path = output_dir / f"transport_rule_audit_review_{timestamp}.csv"

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    removed_df.to_csv(removed_path, index=False, encoding="utf-8-sig")
    reviewed_df.to_csv(review_path, index=False, encoding="utf-8-sig")

    return summary_path, removed_path, review_path


def run_transport_rule_audit(input_path=MASTER_PATH, min_score=3):
    df = load_csv(input_path)
    base_df = drop_existing_transport_columns(df)
    classified = classify_dataframe(base_df, min_score=min_score)

    removed_df = classified[~classified["es_transporte"]].copy()
    kept_df = classified[classified["es_transporte"]].copy()
    review_df = classified[classified["transport_review_flag"].fillna("") != ""].copy()

    summary = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "input_path": str(input_path),
            "min_score": min_score,
        },
        "results": {
            "input_rows": int(len(df)),
            "kept_rows": int(len(kept_df)),
            "removed_rows": int(len(removed_df)),
            "review_rows": int(len(review_df)),
            "kept_rule_counts": kept_df["transport_rule"].fillna("").value_counts().to_dict(),
            "removed_rule_counts": removed_df["transport_rule"].fillna("").value_counts().to_dict(),
            "review_flag_counts": review_df["transport_review_flag"].fillna("").value_counts().to_dict(),
        },
    }

    summary_path, removed_path, review_path = write_audit_outputs(
        summary,
        removed_df,
        review_df,
    )

    print(f"[INFO] Filas analizadas: {len(df)}")
    print(f"[INFO] Filas que seguirian como transporte: {len(kept_df)}")
    print(f"[INFO] Filas que saldrian del universo: {len(removed_df)}")
    print(f"[INFO] Filas marcadas para revision: {len(review_df)}")
    print(f"[OK] Resumen audit: {summary_path}")
    print(f"[INFO] CSV removidas: {removed_path}")
    print(f"[INFO] CSV revision: {review_path}")

    return {
        "summary_path": summary_path,
        "removed_path": removed_path,
        "review_path": review_path,
        "input_rows": len(df),
        "kept_rows": len(kept_df),
        "removed_rows": len(removed_df),
        "review_rows": len(review_df),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Audita el impacto de las reglas actuales del filtro de transporte."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=MASTER_PATH,
        help="CSV a auditar. Por defecto usa el transport master actual.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=3,
        help="Puntaje minimo para la clasificacion.",
    )
    args = parser.parse_args()

    run_transport_rule_audit(input_path=args.input_file, min_score=args.min_score)


if __name__ == "__main__":
    main()
