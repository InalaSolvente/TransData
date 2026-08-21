import argparse
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "data" / "processed" / "transport" / "audit"

EDUCATION_PATTERNS = [
    r"slep",
    r"escuel",
    r"liceo",
    r"jardin",
    r"sala cuna",
    r"establecimientos educacionales",
    r"alumn",
    r"escolar",
    r"extraescolar",
    r"pedagogic",
    r"actividades academicas",
    r"colegio",
]

HEALTH_PATTERNS = [
    r"salud",
    r"centros de salud",
    r"atencion domiciliaria",
    r"cuidados paliativos",
    r"aps",
    r"farmacia",
    r"fofar",
    r"reas",
    r"medicamentos",
]

SOCIAL_PATTERNS = [
    r"dideco",
    r"adulto mayor",
    r"discapacidad",
    r"red local de apoyos",
    r"chile crece contigo",
    r"prlac",
    r"nin",
    r"niñez",
    r"sename",
    r"deudos",
    r"oficina de la mujer",
    r"mujeres jefas de hogar",
    r"habilidades para la vida",
    r"4a7",
]


def find_latest_file(directory, pattern):
    files = sorted(Path(directory).glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos {pattern} en {directory}")
    return files[-1]


def load_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_text_series(df):
    return (
        df["nombre_licitacion"].fillna("").astype(str)
        + " "
        + df.get("descripcion", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
        + " "
        + df.get("transport_domain_context_hits", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
        + " "
        + df.get("transport_activity_context_hits", pd.Series(index=df.index, dtype=object)).fillna("").astype(str)
    ).str.lower()


def matches_any_pattern(series, patterns):
    mask = pd.Series(False, index=series.index)
    for pattern in patterns:
        mask = mask | series.str.contains(pattern, regex=True, na=False)
    return mask


def assign_review_group(df):
    text = normalize_text_series(df)
    education_mask = matches_any_pattern(text, EDUCATION_PATTERNS)
    health_mask = matches_any_pattern(text, HEALTH_PATTERNS)
    social_mask = matches_any_pattern(text, SOCIAL_PATTERNS)

    review_group = pd.Series("other", index=df.index)
    review_group.loc[social_mask] = "social"
    review_group.loc[health_mask] = "health"
    review_group.loc[education_mask] = "education"
    review_group.loc[education_mask & health_mask] = "education_health"
    review_group.loc[education_mask & social_mask] = "education_social"
    review_group.loc[health_mask & social_mask] = "health_social"
    review_group.loc[education_mask & health_mask & social_mask] = "mixed_domain"
    return review_group


def write_outputs(df_queue, summary, output_dir=AUDIT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    queue_path = output_dir / f"transport_review_queue_{timestamp}.csv"
    summary_path = output_dir / f"transport_review_queue_summary_{timestamp}.json"
    markdown_path = output_dir / f"transport_review_queue_{timestamp}.md"

    df_queue.to_csv(queue_path, index=False, encoding="utf-8-sig")
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    lines = [
        "# Transport Review Queue",
        "",
        f"Generado: `{summary['metadata']['generated_at']}`",
        "",
        "## Resumen",
        "",
        f"- Archivo fuente: `{summary['metadata']['input_path']}`",
        f"- Filas de revisión: `{summary['results']['review_rows']}`",
        f"- Grupos: `{summary['results']['group_counts']}`",
        "",
        "## Recomendación de revisión manual",
        "",
        "1. Priorizar `education`, `health` y `social`.",
        "2. Dejar `other` para el final.",
        "3. Revisar `mixed_mode_review` antes de reconstruir el master.",
        "",
    ]

    for group_name, sample_rows in summary["results"]["group_samples"].items():
        lines.append(f"## {group_name}")
        lines.append("")
        for row in sample_rows:
            lines.append(
                f"- `{row['codigo_licitacion']}` | `{row['transport_review_flag']}` | {row['nombre_licitacion']}"
            )
        lines.append("")

    with markdown_path.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    return queue_path, summary_path, markdown_path


def run_transport_review_queue(input_path=None):
    if input_path is None:
        input_path = find_latest_file(AUDIT_DIR, "transport_rule_audit_review_*.csv")

    df = load_csv(input_path)
    df = df.copy()
    df["review_group"] = assign_review_group(df)

    columns_front = [
        "codigo_licitacion",
        "nombre_licitacion",
        "transport_rule",
        "transport_review_flag",
        "review_group",
        "transport_score",
        "transport_positive_hits",
        "transport_domain_context_hits",
        "transport_activity_context_hits",
        "transport_exclusion_hits",
    ]
    existing_columns = [column for column in columns_front if column in df.columns]
    other_columns = [column for column in df.columns if column not in existing_columns]
    df = df[existing_columns + other_columns]

    group_counts = df["review_group"].value_counts().to_dict()
    group_samples = {}
    for group_name, df_group in df.groupby("review_group"):
        group_samples[group_name] = (
            df_group[["codigo_licitacion", "nombre_licitacion", "transport_review_flag"]]
            .head(12)
            .to_dict(orient="records")
        )

    summary = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "input_path": str(input_path),
        },
        "results": {
            "review_rows": int(len(df)),
            "group_counts": group_counts,
            "flag_counts": df["transport_review_flag"].fillna("").value_counts().to_dict(),
            "group_samples": group_samples,
        },
    }

    queue_path, summary_path, markdown_path = write_outputs(df, summary)

    print(f"[INFO] Filas de revisión agrupadas: {len(df)}")
    print(f"[INFO] Conteo por grupo: {group_counts}")
    print(f"[OK] Cola de revisión CSV: {queue_path}")
    print(f"[INFO] Resumen cola: {summary_path}")
    print(f"[INFO] Cola Markdown: {markdown_path}")

    return {
        "queue_path": queue_path,
        "summary_path": summary_path,
        "markdown_path": markdown_path,
        "review_rows": len(df),
        "group_counts": group_counts,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Agrupa las filas en revisión del filtro de transporte para facilitar revisión manual posterior."
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help="CSV de revisión del audit. Si no se indica, usa el más reciente.",
    )
    args = parser.parse_args()

    run_transport_review_queue(input_path=args.input_file)


if __name__ == "__main__":
    main()
