# src/ingest/mp_ingest_batch.py

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# =========================================================
# PATH DEL PROYECTO
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

load_dotenv(PROJECT_ROOT / ".env")

from ingest.mp_ingest import (
    QUERY_MODE,
    SKIP_EXISTING_DAYS,
    build_query_key,
    format_mp_date,
    discover_ingest_coverage,
    normalize_estados,
    run_ingest,
)


RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
BATCH_SLEEP_BETWEEN_WINDOWS = float(os.getenv("BATCH_SLEEP_BETWEEN_WINDOWS", "10"))


def generar_ventanas(start_day, end_day, window_days):
    ventanas = []
    actual = start_day

    while actual <= end_day:
        fin = min(actual + window_days - 1, end_day)
        ventanas.append((actual, fin))
        actual = fin + 1

    return ventanas


def build_days_to_process(start_day, end_day, query_mode, skip_existing_days):
    all_days = list(range(start_day, end_day + 1))
    if not skip_existing_days:
        return all_days

    coverage = discover_ingest_coverage()
    success_keys = coverage.get("success_keys", set())
    pending_days = []

    for day in all_days:
        fecha_consulta = format_mp_date(day)
        day_key = build_query_key(
            fecha_consulta,
            query_mode,
            None if query_mode == "day" else None,
        )

        if query_mode == "day":
            if day_key not in success_keys:
                pending_days.append(day)
        else:
            # En day_state no inferimos cobertura parcial por estado aqui.
            # Se deja que run_ingest salte query por query segun cobertura real.
            pending_days.append(day)

    return pending_days


def generar_ventanas_desde_dias(days, window_days):
    if not days:
        return []

    ventanas = []
    current_start = days[0]
    current_end = days[0]
    count = 1

    for day in days[1:]:
        contiguous = day == current_end + 1
        if contiguous and count < window_days:
            current_end = day
            count += 1
            continue

        ventanas.append((current_start, current_end))
        current_start = day
        current_end = day
        count = 1

    ventanas.append((current_start, current_end))
    return ventanas


def load_ingest_metadata(output_path):
    with open(output_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    return payload.get("metadata", {})


def classify_window(metadata):
    total_expected = int(metadata.get("total_expected_queries") or 0)
    total_failed = int(metadata.get("total_failed_queries") or 0)
    total_records = int(metadata.get("total_records_found") or 0)

    if total_expected > 0 and total_failed >= total_expected:
        return "completed_all_queries_failed"

    if total_records > 0:
        return "completed_with_records"

    return "completed_without_records"


def main():
    batch_start = int(os.getenv("BATCH_START_DAY", "1"))
    batch_end = int(os.getenv("BATCH_END_DAY", "270"))
    window_days = int(os.getenv("WINDOW_DAYS", "30"))
    estados = normalize_estados(os.getenv("ESTADOS"))
    query_mode = os.getenv("MP_QUERY_MODE", QUERY_MODE).strip().lower()
    skip_existing_days = os.getenv("MP_SKIP_EXISTING_DAYS", str(SKIP_EXISTING_DAYS)).strip().lower() in {
        "1", "true", "yes", "si"
    }

    if batch_start < 1:
        raise ValueError("BATCH_START_DAY debe ser >= 1")

    if batch_end < batch_start:
        raise ValueError("BATCH_END_DAY debe ser >= BATCH_START_DAY")

    if window_days <= 0:
        raise ValueError("WINDOW_DAYS debe ser > 0")

    target_days = build_days_to_process(
        start_day=batch_start,
        end_day=batch_end,
        query_mode=query_mode,
        skip_existing_days=skip_existing_days,
    )
    ventanas = generar_ventanas_desde_dias(target_days, window_days)

    print("\n[INFO] Iniciando ingest batch...")
    print(f"[INFO] Rango total: días {batch_start} a {batch_end}")
    print(f"[INFO] Tamaño de ventana: {window_days} días")
    print(f"[INFO] Estados: {estados}")
    print(f"[INFO] Query mode: {query_mode}")
    print(f"[INFO] Skip existing days: {skip_existing_days}")
    print(f"[INFO] Dias pendientes de consultar: {len(target_days)}")
    print(f"[INFO] Total de ventanas a ejecutar: {len(ventanas)}")
    print(f"[INFO] Pausa entre ventanas: {BATCH_SLEEP_BETWEEN_WINDOWS}s")

    if not ventanas:
        print("[INFO] No hay dias pendientes en el rango solicitado.")
        return

    archivos_generados = []
    ventanas_fallidas = []

    total_ventanas = len(ventanas)
    ventanas_exitosas = 0
    ventanas_con_datos = 0
    ventanas_sin_datos = 0
    ventanas_todas_fallidas = 0
    started_at = datetime.now().isoformat()

    for i, (inicio, fin) in enumerate(ventanas, start=1):
        print("\n" + "=" * 70)
        print(f"[INFO] Ventana {i}/{total_ventanas} -> días {inicio} a {fin}")
        print("=" * 70)

        try:
            output_path = run_ingest(
                start_day=inicio,
                end_day=fin,
                estados=estados,
                query_mode=query_mode,
                skip_existing_days=skip_existing_days,
            )

            metadata = load_ingest_metadata(output_path)
            status = classify_window(metadata)

            archivos_generados.append({
                "start_day": inicio,
                "end_day": fin,
                "file": str(output_path),
                "status": status,
                "total_expected_queries": metadata.get("total_expected_queries"),
                "total_failed_queries": metadata.get("total_failed_queries"),
                "total_records_found": metadata.get("total_records_found")
            })
            ventanas_exitosas += 1

            if status == "completed_with_records":
                ventanas_con_datos += 1
            elif status == "completed_all_queries_failed":
                ventanas_todas_fallidas += 1
            else:
                ventanas_sin_datos += 1

        except Exception as e:
            print(f"[ERROR] Falló la ventana {inicio}-{fin}: {e}")
            ventanas_fallidas.append({
                "start_day": inicio,
                "end_day": fin,
                "error": str(e)
            })

        if i < total_ventanas and BATCH_SLEEP_BETWEEN_WINDOWS > 0:
            print(f"[INFO] Pausa entre ventanas: {BATCH_SLEEP_BETWEEN_WINDOWS}s")
            time.sleep(BATCH_SLEEP_BETWEEN_WINDOWS)

    ended_at = datetime.now().isoformat()

    resumen = {
        "metadata": {
            "type": "ingest_batch_summary",
            "generated_at": ended_at,
            "started_at": started_at,
            "batch_start_day": batch_start,
            "batch_end_day": batch_end,
            "window_days": window_days,
            "sleep_between_windows": BATCH_SLEEP_BETWEEN_WINDOWS,
            "query_mode": query_mode,
            "skip_existing_days": skip_existing_days,
            "estados": estados
        },
        "results": {
            "dias_pendientes_consultados": len(target_days),
            "total_ventanas": total_ventanas,
            "ventanas_exitosas": ventanas_exitosas,
            "ventanas_fallidas": len(ventanas_fallidas),
            "ventanas_con_datos": ventanas_con_datos,
            "ventanas_sin_datos": ventanas_sin_datos,
            "ventanas_todas_las_consultas_fallidas": ventanas_todas_fallidas
        },
        "successful_windows": archivos_generados,
        "failed_windows": ventanas_fallidas
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    resumen_path = RAW_DIR / f"mp_batch_summary_{batch_start}_{batch_end}_{timestamp}.json"

    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    print("\n[INFO] Batch finalizado.")
    print(f"[INFO] Ventanas totales: {total_ventanas}")
    print(f"[INFO] Ventanas exitosas: {ventanas_exitosas}")
    print(f"[INFO] Ventanas con datos: {ventanas_con_datos}")
    print(f"[INFO] Ventanas sin datos: {ventanas_sin_datos}")
    print(f"[INFO] Ventanas con todas las consultas fallidas: {ventanas_todas_fallidas}")
    print(f"[INFO] Ventanas fallidas: {len(ventanas_fallidas)}")
    print(f"[INFO] Resumen guardado en: {resumen_path}")

    if archivos_generados:
        print("\n[INFO] Archivos generados:")
        for a in archivos_generados:
            print(f" - {a['file']} [{a['status']}]")

    if ventanas_fallidas:
        print("\n[WARN] Ventanas con error:")
        for v in ventanas_fallidas:
            print(f" - {v['start_day']}-{v['end_day']}: {v['error']}")


if __name__ == "__main__":
    main()
