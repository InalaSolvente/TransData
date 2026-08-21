import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from mp_parse_licitaciones import RAW_DIR, PROCESSED_DIR, parse_raw_file


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH)


def parse_bool(value, default=False):
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    s = str(value).strip().lower()
    if s in {"1", "true", "yes", "si"}:
        return True
    if s in {"0", "false", "no"}:
        return False

    return default


def discover_raw_files(raw_dir, pattern):
    return sorted(raw_dir.glob(pattern), key=lambda p: p.stat().st_mtime)


def write_summary(summary):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PROCESSED_DIR / f"mp_transform_summary_{timestamp}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return path


def run_transform_batch(raw_dir=RAW_DIR, pattern="mp_raw_*.json", overwrite=False):
    raw_dir = Path(raw_dir)
    files = discover_raw_files(raw_dir, pattern)

    started_at = datetime.now().isoformat()
    results = []

    print("\n[INFO] Iniciando transform batch...")
    print(f"[INFO] Raw dir: {raw_dir}")
    print(f"[INFO] Pattern: {pattern}")
    print(f"[INFO] Archivos encontrados: {len(files)}")
    print(f"[INFO] Overwrite: {overwrite}")

    for i, raw_path in enumerate(files, start=1):
        print(f"\n[INFO] Transform {i}/{len(files)}: {raw_path.name}")

        try:
            result = parse_raw_file(raw_path, output_dir=PROCESSED_DIR, overwrite=overwrite)
            results.append(result)

            if result["status"] == "processed":
                print(f"[OK] Filas: {result['rows']} -> {result['output_file']}")
            elif result["status"] == "skipped_existing":
                print(f"[INFO] Saltado; output existente: {result['output_file']}")
            else:
                print(f"[WARN] Sin registros procesables: {result.get('message')}")

        except Exception as e:
            print(f"[ERROR] Fallo transformando {raw_path.name}: {e}")
            results.append({
                "raw_file": raw_path.name,
                "status": "failed",
                "error": str(e),
                "output_file": None,
                "rows": 0,
                "parsed_at": datetime.now().isoformat(),
            })

    ended_at = datetime.now().isoformat()

    counts = {
        "processed": sum(1 for r in results if r.get("status") == "processed"),
        "skipped_existing": sum(1 for r in results if r.get("status") == "skipped_existing"),
        "no_records": sum(1 for r in results if r.get("status") == "no_records"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
    }

    summary = {
        "metadata": {
            "type": "transform_batch_summary",
            "started_at": started_at,
            "ended_at": ended_at,
            "raw_dir": str(raw_dir),
            "processed_dir": str(PROCESSED_DIR),
            "pattern": pattern,
            "overwrite": overwrite,
        },
        "results": {
            "total_raw_files": len(files),
            **counts,
            "total_rows_processed": sum(r.get("rows") or 0 for r in results),
        },
        "files": results,
    }

    summary_path = write_summary(summary)

    print("\n[INFO] Transform batch finalizado.")
    print(f"[INFO] Procesados: {counts['processed']}")
    print(f"[INFO] Saltados existentes: {counts['skipped_existing']}")
    print(f"[INFO] Sin registros: {counts['no_records']}")
    print(f"[INFO] Fallidos: {counts['failed']}")
    print(f"[INFO] Resumen guardado en: {summary_path}")

    return summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Procesa en batch raws de MercadoPublico desde data/raw."
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directorio donde buscar raws JSON.",
    )
    parser.add_argument(
        "--pattern",
        default=os.getenv("TRANSFORM_RAW_PATTERN", "mp_raw_*.json"),
        help="Patron glob de raws a procesar.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=parse_bool(os.getenv("TRANSFORM_FORCE_REPROCESS"), default=False),
        help="Reprocesa aunque ya exista el CSV de salida.",
    )
    args = parser.parse_args()

    run_transform_batch(
        raw_dir=args.raw_dir,
        pattern=args.pattern,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
