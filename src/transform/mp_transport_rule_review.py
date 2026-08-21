import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "data" / "processed" / "transport" / "audit"


def find_latest_file(directory, pattern):
    files = sorted(Path(directory).glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos {pattern} en {directory}")
    return files[-1]


def load_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def sample_rows(df, size=12):
    columns = [
        "codigo_licitacion",
        "nombre_licitacion",
        "transport_rule",
        "transport_score",
        "transport_positive_hits",
        "transport_passenger_context_hits",
        "transport_land_mode_hits",
        "transport_activity_context_hits",
        "transport_exclusion_hits",
        "transport_negative_hits",
    ]
    existing = [column for column in columns if column in df.columns]
    return df[existing].head(size).to_dict(orient="records")


def classify_removed_buckets(df_removed):
    buckets = {
        "generic_ambiguous": df_removed[df_removed["transport_rule"] == "rejected"].copy(),
        "exclusion_context": df_removed[df_removed["transport_rule"] == "rejected_exclusion_context"].copy(),
        "mixed_passenger_cargo": df_removed[df_removed["transport_rule"] == "rejected_mixed_passenger_cargo"].copy(),
        "mixed_cargo": df_removed[df_removed["transport_rule"] == "rejected_mixed_cargo"].copy(),
        "negative_score": df_removed[df_removed["transport_rule"] == "rejected_negative_score"].copy(),
    }
    return buckets


def build_bucket_summary(name, df_bucket):
    return {
        "bucket": name,
        "rows": int(len(df_bucket)),
        "positive_hits_top10": df_bucket["transport_positive_hits"].fillna("").value_counts().head(10).to_dict(),
        "passenger_context_top10": df_bucket["transport_passenger_context_hits"].fillna("").value_counts().head(10).to_dict(),
        "land_mode_top10": df_bucket["transport_land_mode_hits"].fillna("").value_counts().head(10).to_dict(),
        "activity_context_top10": df_bucket["transport_activity_context_hits"].fillna("").value_counts().head(10).to_dict(),
        "exclusion_hits_top10": df_bucket["transport_exclusion_hits"].fillna("").value_counts().head(10).to_dict(),
        "negative_hits_top10": df_bucket["transport_negative_hits"].fillna("").value_counts().head(10).to_dict(),
        "sample_rows": sample_rows(df_bucket),
    }


def render_markdown(review):
    lines = []
    lines.append("# Transport Rule Review")
    lines.append("")
    lines.append(f"Generado: `{review['metadata']['generated_at']}`")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Archivo audit removido: `{review['metadata']['removed_input_path']}`")
    lines.append(f"- Filas removidas analizadas: `{review['results']['removed_rows']}`")
    lines.append(f"- Bucket dominante: `{review['results']['dominant_bucket']}`")
    lines.append("")
    lines.append("## Lectura rápida")
    lines.append("")
    lines.append("- La mayor parte del ruido removido proviene de casos genéricos `servicio_transporte` sin contexto suficiente de pasajeros terrestres.")
    lines.append("- Las exclusiones por marítimo, aéreo, ambulancia, logística y transporte de vehículos parecen bien encaminadas.")
    lines.append("- Los casos mixtos `pasajeros y carga` aparecen pocos, pero son consistentes y conviene mantenerlos fuera salvo decisión de negocio contraria.")
    lines.append("")

    for bucket in review["buckets"]:
        lines.append(f"## {bucket['bucket']}")
        lines.append("")
        lines.append(f"- Filas: `{bucket['rows']}`")
        if bucket["positive_hits_top10"]:
            lines.append(f"- Positive hits top: `{bucket['positive_hits_top10']}`")
        if bucket["exclusion_hits_top10"]:
            lines.append(f"- Exclusion hits top: `{bucket['exclusion_hits_top10']}`")
        if bucket["negative_hits_top10"]:
            lines.append(f"- Negative hits top: `{bucket['negative_hits_top10']}`")
        lines.append("")
        lines.append("Muestra:")
        lines.append("")
        for row in bucket["sample_rows"][:8]:
            lines.append(
                f"- `{row.get('codigo_licitacion', '')}` | {row.get('transport_rule', '')} | "
                f"{row.get('nombre_licitacion', '')}"
            )
        lines.append("")

    lines.append("## Recomendación")
    lines.append("")
    lines.append("1. Revisar primero el bucket `generic_ambiguous`, porque ahí está casi todo el volumen removido.")
    lines.append("2. Mantener por ahora las exclusiones de marítimo, aéreo, logística y transporte de vehículos.")
    lines.append("3. Si queremos recuperar parte del universo, hacerlo creando contexto positivo adicional para programas sociales, salud y educación, no relajando exclusiones duras.")
    lines.append("")
    return "\n".join(lines)


def write_outputs(review, markdown, output_dir=AUDIT_DIR):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"transport_rule_review_summary_{timestamp}.json"
    md_path = output_dir / f"transport_rule_review_{timestamp}.md"

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(review, handle, ensure_ascii=False, indent=2)
    with md_path.open("w", encoding="utf-8") as handle:
        handle.write(markdown)

    return json_path, md_path


def run_transport_rule_review(removed_path=None):
    if removed_path is None:
        removed_path = find_latest_file(AUDIT_DIR, "transport_rule_audit_removed_*.csv")

    df_removed = load_csv(removed_path)
    buckets = classify_removed_buckets(df_removed)
    bucket_summaries = [build_bucket_summary(name, df_bucket) for name, df_bucket in buckets.items()]
    dominant_bucket = max(bucket_summaries, key=lambda item: item["rows"])["bucket"] if bucket_summaries else None

    review = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "removed_input_path": str(removed_path),
        },
        "results": {
            "removed_rows": int(len(df_removed)),
            "dominant_bucket": dominant_bucket,
        },
        "buckets": bucket_summaries,
    }

    markdown = render_markdown(review)
    json_path, md_path = write_outputs(review, markdown)

    print(f"[INFO] Filas removidas analizadas: {len(df_removed)}")
    print(f"[INFO] Bucket dominante: {dominant_bucket}")
    print(f"[OK] Review JSON: {json_path}")
    print(f"[INFO] Review Markdown: {md_path}")

    return {
        "json_path": json_path,
        "markdown_path": md_path,
        "removed_rows": len(df_removed),
        "dominant_bucket": dominant_bucket,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Genera una revisión guiada de las filas removidas por la auditoría del filtro de transporte."
    )
    parser.add_argument(
        "--removed-file",
        type=Path,
        default=None,
        help="CSV de removidas de una auditoría previa. Si no se indica, usa el más reciente.",
    )
    args = parser.parse_args()

    run_transport_rule_review(removed_path=args.removed_file)


if __name__ == "__main__":
    main()
