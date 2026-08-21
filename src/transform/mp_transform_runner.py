import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from mp_append_master import MASTER_DIR, append_processed_files, find_processed_files
from apply_transport_manual_review import (
    DEFAULT_MANUAL_REVIEW_CSV,
    DEFAULT_MANUAL_REVIEW_SUMMARY,
    TRANSPORT_MASTER_CORE_PATH,
    rebuild_transport_master_core,
)
from mp_enrich_details import TRANSPORT_MASTER_PATH, enrich_transport_master
from mp_prepare_analytics import ANALYTICS_DIR, prepare_analytics
from mp_quality_check import REPORTS_DIR as QUALITY_REPORTS_DIR, run_quality_check
from mp_prepare_serving import SERVING_DIR, prepare_serving
from mp_refresh import TRANSPORT_HISTORY_PATH, refresh_master
from mp_transform_batch import run_transform_batch
from mp_transport_filter import run_transport_selection


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
PIPELINE_DIR = PROCESSED_DIR / "pipeline"
TRANSPORT_MASTER_DIR = MASTER_DIR


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def env_int(name, default=None):
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'")
    if value == "":
        return default
    return int(value)


def env_float(name, default):
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'")
    if value == "":
        return default
    return float(value)


def env_bool(name, default=False):
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'").lower()
    if value in {"true", "1", "si", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return default


def env_str(name, default=None):
    load_env()
    raw = os.getenv(name, "")
    if raw is None:
        return default
    value = raw.strip().strip('"').strip("'")
    if value == "":
        return default
    return value


def resolve_repo_path(path_like):
    if path_like is None:
        return None
    path = Path(path_like)
    if path.is_absolute():
        return path
    return ROOT / path


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_processed_files_from_summary(summary):
    processed_files = []
    for item in summary.get("files", []):
        if item.get("status") == "processed" and item.get("output_file"):
            processed_files.append(Path(item["output_file"]))
    return processed_files


def write_runner_summary(summary):
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PIPELINE_DIR / f"mp_transform_runner_summary_{timestamp}.json"

    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return path


def resolve_processed_files_for_transport(new_processed_files):
    if not TRANSPORT_MASTER_PATH.exists():
        bootstrap_files = find_processed_files(latest_only=False)
        return bootstrap_files, "bootstrap_all_processed"

    if new_processed_files:
        return new_processed_files, "new_processed"

    return [], "no_new_processed"


def run_transform_runner(
    raw_pattern="mp_raw_*.json",
    overwrite=False,
    min_score=3,
    enrich_limit=None,
    enrich_only_errors=False,
    enrich_max_attempts_per_code=None,
    enrich_sleep_sec=None,
    enrich_pause_every=None,
    enrich_pause_seconds=None,
    run_refresh=None,
    refresh_limit=None,
    refresh_timeout=None,
    refresh_retries=None,
    refresh_backoff_seconds=None,
    refresh_sleep_sec=None,
    refresh_force_terminal_awards=None,
    refresh_only_never_refreshed=None,
    run_manual_review=None,
    manual_review_file=None,
    manual_review_summary_file=None,
    transport_core_master_path=None,
    run_analytics=None,
    analytics_output_dir=None,
    run_quality=None,
    quality_output_dir=None,
    run_serving=None,
    serving_output_dir=None,
    sync_derived_after_master_change=None,
):
    started_at = datetime.now().isoformat()
    if enrich_limit is None:
        enrich_limit = env_int("MP_ENRICH_LIMIT", None)
    if enrich_sleep_sec is None:
        enrich_sleep_sec = env_float("MP_ENRICH_SLEEP_SEC", 0.8)
    if enrich_pause_every is None:
        enrich_pause_every = env_int("MP_ENRICH_PAUSE_EVERY", 100)
    if enrich_pause_seconds is None:
        enrich_pause_seconds = env_float("MP_ENRICH_PAUSE_SECONDS", 4.0)
    if run_refresh is None:
        run_refresh = env_bool("MP_RUN_REFRESH", False)
    if refresh_limit is None:
        refresh_limit = env_int("MP_REFRESH_LIMIT", 200)
    if refresh_timeout is None:
        refresh_timeout = env_int("MP_REFRESH_TIMEOUT", 25)
    if refresh_retries is None:
        refresh_retries = env_int("MP_REFRESH_MAX_RETRIES", 5)
    if refresh_backoff_seconds is None:
        refresh_backoff_seconds = env_float("MP_REFRESH_BACKOFF_SECONDS", 1.5)
    if refresh_sleep_sec is None:
        refresh_sleep_sec = env_float("MP_REFRESH_SLEEP_SEC", 0.6)
    if refresh_force_terminal_awards is None:
        refresh_force_terminal_awards = env_bool("MP_REFRESH_FORCE_TERMINAL_AWARDS", True)
    if refresh_only_never_refreshed is None:
        refresh_only_never_refreshed = env_bool("MP_REFRESH_ONLY_NEVER_REFRESHED", False)
    if run_manual_review is None:
        run_manual_review = env_bool("MP_RUN_TRANSPORT_MANUAL_REVIEW", True)
    if manual_review_file is None:
        manual_review_file = resolve_repo_path(
            env_str("MP_TRANSPORT_MANUAL_REVIEW_FILE", str(DEFAULT_MANUAL_REVIEW_CSV))
        )
    if manual_review_summary_file is None:
        manual_review_summary_file = resolve_repo_path(
            env_str("MP_TRANSPORT_MANUAL_REVIEW_SUMMARY_FILE", str(DEFAULT_MANUAL_REVIEW_SUMMARY))
        )
    if transport_core_master_path is None:
        transport_core_master_path = TRANSPORT_MASTER_CORE_PATH
    if run_analytics is None:
        run_analytics = env_bool("MP_RUN_ANALYTICS", False)
    if analytics_output_dir is None:
        analytics_output_dir = ANALYTICS_DIR
    if run_quality is None:
        run_quality = env_bool("MP_RUN_QUALITY_CHECK", False)
    if quality_output_dir is None:
        quality_output_dir = QUALITY_REPORTS_DIR
    if run_serving is None:
        run_serving = env_bool("MP_RUN_SERVING", False)
    if serving_output_dir is None:
        serving_output_dir = SERVING_DIR
    if sync_derived_after_master_change is None:
        sync_derived_after_master_change = env_bool("MP_SYNC_DERIVED_AFTER_MASTER_CHANGE", True)

    print("\n[INFO] Paso 1/8: transform batch")
    transform_summary_path = run_transform_batch(
        raw_dir=RAW_DIR,
        pattern=raw_pattern,
        overwrite=overwrite,
    )
    transform_summary = load_json(transform_summary_path)
    new_processed_files = extract_processed_files_from_summary(transform_summary)

    processed_files_for_transport, transport_source_label = resolve_processed_files_for_transport(
        new_processed_files
    )

    transport_selection_result = {
        "executed": False,
        "source_label": transport_source_label,
        "source_files": 0,
        "transport_rows": 0,
        "filtered_path": None,
        "summary_path": None,
    }

    append_result = {
        "executed": False,
        "processed_files_used": 0,
        "master_path": str(TRANSPORT_MASTER_PATH),
        "summary_path": None,
    }

    if processed_files_for_transport:
        print("\n[INFO] Paso 2/8: seleccion transporte")
        selection_outputs = run_transport_selection(
            processed_files_for_transport,
            min_score=min_score,
            source_label=transport_source_label,
        )
        transport_selection_result = {
            "executed": True,
            "source_label": transport_source_label,
            "source_files": selection_outputs["source_files"],
            "transport_rows": selection_outputs["transport_rows"],
            "filtered_path": str(selection_outputs["filtered_path"]),
            "summary_path": str(selection_outputs["summary_path"]),
        }

        if selection_outputs["transport_rows"] > 0:
            print("\n[INFO] Paso 3/8: append transport master")
            master_path, append_summary_path = append_processed_files(
                processed_files=[Path(selection_outputs["filtered_path"])],
                master_path=TRANSPORT_MASTER_PATH,
            )
            append_result = {
                "executed": True,
                "processed_files_used": 1,
                "master_path": str(master_path),
                "summary_path": str(append_summary_path),
            }
        else:
            print("\n[INFO] Paso 3/8: append transport master saltado (sin candidatos)")
    else:
        print("\n[INFO] Paso 2/8: seleccion transporte saltada (sin processed nuevos y transport master ya existe)")
        print("[INFO] Paso 3/8: append transport master saltado")

    master_changed = bool(append_result["executed"])

    enrich_result = {
        "executed": False,
        "master_path": str(TRANSPORT_MASTER_PATH),
        "pending_codes": 0,
        "errors": 0,
    }

    if TRANSPORT_MASTER_PATH.exists():
        print("\n[INFO] Paso 4/8: enrich transport master")
        enrich_summary = enrich_transport_master(
            master_path=TRANSPORT_MASTER_PATH,
            limit=enrich_limit,
            sleep_sec=enrich_sleep_sec,
            only_errors=enrich_only_errors,
            max_attempts_per_code=enrich_max_attempts_per_code,
            pause_every=enrich_pause_every,
            pause_seconds=enrich_pause_seconds,
        )
        enrich_result = {
            "executed": True,
            **enrich_summary,
        }
        if enrich_summary.get("successes", 0) > 0:
            master_changed = True
    else:
        print("\n[INFO] Paso 4/8: enrich saltado (transport master no existe)")

    refresh_result = {
        "executed": False,
        "enabled": bool(run_refresh),
        "master_path": str(TRANSPORT_MASTER_PATH),
        "history_path": str(TRANSPORT_HISTORY_PATH),
        "selected_rows": 0,
        "errors": 0,
    }

    if run_refresh and TRANSPORT_MASTER_PATH.exists():
        print("\n[INFO] Paso 5/8: refresh transport master")
        refresh_summary = refresh_master(
            master_path=TRANSPORT_MASTER_PATH,
            history_path=TRANSPORT_HISTORY_PATH,
            limit=refresh_limit,
            timeout=refresh_timeout,
            retries=refresh_retries,
            retry_backoff_seconds=refresh_backoff_seconds,
            sleep_sec=refresh_sleep_sec,
            force_terminal_awards=refresh_force_terminal_awards,
            only_never_refreshed=refresh_only_never_refreshed,
        )
        refresh_result = {
            "executed": True,
            "enabled": True,
            **refresh_summary,
        }
        if refresh_summary.get("changed_rows", 0) > 0 or refresh_summary.get("successful_rows", 0) > 0:
            master_changed = True
    elif run_refresh:
        print("\n[INFO] Paso 5/8: refresh saltado (transport master no existe)")
    else:
        print("\n[INFO] Paso 5/8: refresh saltado (deshabilitado)")

    manual_review_result = {
        "executed": False,
        "enabled": bool(run_manual_review),
        "manual_review_file": str(manual_review_file),
        "core_master_path": str(transport_core_master_path),
    }

    if run_manual_review and TRANSPORT_MASTER_PATH.exists():
        print("\n[INFO] Paso 6/9: aplicar revision manual de transporte")
        manual_review_result = {
            "executed": True,
            "enabled": True,
            **rebuild_transport_master_core(
                master_path=TRANSPORT_MASTER_PATH,
                manual_review_path=manual_review_file,
                manual_review_summary_path=manual_review_summary_file,
                core_master_path=Path(transport_core_master_path),
            ),
        }
        if manual_review_result.get("included_core_rows", 0) > 0:
            master_changed = True
    elif run_manual_review:
        print("\n[INFO] Paso 6/9: revision manual saltada (transport master no existe)")
    else:
        print("\n[INFO] Paso 6/9: revision manual saltada (deshabilitada)")

    run_analytics_effective = bool(run_analytics) or (sync_derived_after_master_change and master_changed)
    run_quality_effective = bool(run_quality) or (sync_derived_after_master_change and master_changed)
    run_serving_effective = bool(run_serving) or (sync_derived_after_master_change and master_changed)

    analytics_result = {
        "executed": False,
        "enabled": bool(run_analytics),
        "effective_enabled": run_analytics_effective,
        "output_dir": str(analytics_output_dir),
    }

    derived_master_path = Path(transport_core_master_path) if Path(transport_core_master_path).exists() else TRANSPORT_MASTER_PATH

    if run_analytics_effective and derived_master_path.exists():
        print("\n[INFO] Paso 7/9: preparar capa analitica")
        analytics_summary = prepare_analytics(
            master_path=derived_master_path,
            output_dir=Path(analytics_output_dir),
        )
        analytics_result = {
            "executed": True,
            "enabled": bool(run_analytics),
            "effective_enabled": True,
            **analytics_summary,
        }
    elif run_analytics_effective:
        print("\n[INFO] Paso 7/9: analitica saltada (transport master no existe)")
    else:
        print("\n[INFO] Paso 7/9: analitica saltada (deshabilitada)")

    quality_result = {
        "executed": False,
        "enabled": bool(run_quality),
        "effective_enabled": run_quality_effective,
        "output_dir": str(quality_output_dir),
    }

    if run_quality_effective and derived_master_path.exists():
        print("\n[INFO] Paso 8/9: quality check transport master")
        quality_summary = run_quality_check(
            master_path=derived_master_path,
            output_dir=Path(quality_output_dir),
        )
        quality_result = {
            "executed": True,
            "enabled": bool(run_quality),
            "effective_enabled": True,
            **quality_summary,
        }
    elif run_quality_effective:
        print("\n[INFO] Paso 8/9: quality check saltado (transport master no existe)")
    else:
        print("\n[INFO] Paso 8/9: quality check saltado (deshabilitado)")

    serving_result = {
        "executed": False,
        "enabled": bool(run_serving),
        "effective_enabled": run_serving_effective,
        "output_dir": str(serving_output_dir),
    }

    if run_serving_effective and derived_master_path.exists():
        print("\n[INFO] Paso 9/9: preparar capa de serving")
        serving_summary = prepare_serving(
            master_path=derived_master_path,
            output_dir=Path(serving_output_dir),
        )
        serving_result = {
            "executed": True,
            "enabled": bool(run_serving),
            "effective_enabled": True,
            **serving_summary,
        }
    elif run_serving_effective:
        print("\n[INFO] Paso 9/9: serving saltado (transport master no existe)")
    else:
        print("\n[INFO] Paso 9/9: serving saltado (deshabilitado)")

    ended_at = datetime.now().isoformat()

    summary = {
        "metadata": {
            "type": "transform_runner_summary",
            "started_at": started_at,
            "ended_at": ended_at,
            "raw_pattern": raw_pattern,
            "overwrite": overwrite,
            "min_score": min_score,
            "enrich_limit": enrich_limit,
            "enrich_only_errors": enrich_only_errors,
            "enrich_max_attempts_per_code": enrich_max_attempts_per_code,
            "enrich_sleep_sec": enrich_sleep_sec,
            "enrich_pause_every": enrich_pause_every,
            "enrich_pause_seconds": enrich_pause_seconds,
            "run_refresh": run_refresh,
            "refresh_limit": refresh_limit,
            "refresh_timeout": refresh_timeout,
            "refresh_retries": refresh_retries,
            "refresh_backoff_seconds": refresh_backoff_seconds,
            "refresh_sleep_sec": refresh_sleep_sec,
            "refresh_force_terminal_awards": refresh_force_terminal_awards,
            "refresh_only_never_refreshed": refresh_only_never_refreshed,
            "run_manual_review": run_manual_review,
            "manual_review_file": str(manual_review_file),
            "manual_review_summary_file": str(manual_review_summary_file),
            "transport_core_master_path": str(transport_core_master_path),
            "run_analytics": run_analytics,
            "analytics_output_dir": str(analytics_output_dir),
            "run_quality": run_quality,
            "quality_output_dir": str(quality_output_dir),
            "run_serving": run_serving,
            "serving_output_dir": str(serving_output_dir),
            "sync_derived_after_master_change": sync_derived_after_master_change,
            "master_changed": master_changed,
        },
        "steps": {
            "transform_summary_path": str(transform_summary_path),
            "transport_selection_result": transport_selection_result,
            "append_result": append_result,
            "enrich_result": enrich_result,
            "refresh_result": refresh_result,
            "manual_review_result": manual_review_result,
            "analytics_result": analytics_result,
            "quality_result": quality_result,
            "serving_result": serving_result,
        },
    }

    summary_path = write_runner_summary(summary)
    print("\n[OK] Runner finalizado.")
    print(f"[INFO] Resumen runner: {summary_path}")

    return summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta transform, selección transporte, transport master, revisión manual, enrich y refresh."
    )
    parser.add_argument(
        "--raw-pattern",
        default="mp_raw_*.json",
        help="Patron glob para raws a procesar.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocesa raws aunque ya exista output processed.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=3,
        help="Puntaje minimo para clasificar transporte.",
    )
    parser.add_argument(
        "--enrich-limit",
        type=int,
        default=None,
        help="Limita codigos a enriquecer en esta corrida. Si no se indica, usa MP_ENRICH_LIMIT del .env.",
    )
    parser.add_argument(
        "--enrich-only-errors",
        action="store_true",
        help="Enriquece solo codigos con error previo.",
    )
    parser.add_argument(
        "--enrich-max-attempts-per-code",
        type=int,
        default=None,
        help="Limita reintentos acumulados por codigo en enrich.",
    )
    parser.add_argument(
        "--enrich-sleep-sec",
        type=float,
        default=None,
        help="Pausa entre consultas de enrich. Si no se indica, usa MP_ENRICH_SLEEP_SEC del .env.",
    )
    parser.add_argument(
        "--enrich-pause-every",
        type=int,
        default=None,
        help="Pausa corta cada N codigos procesados. Si no se indica, usa MP_ENRICH_PAUSE_EVERY del .env.",
    )
    parser.add_argument(
        "--enrich-pause-seconds",
        type=float,
        default=None,
        help="Duracion de la pausa corta. Si no se indica, usa MP_ENRICH_PAUSE_SECONDS del .env.",
    )
    parser.add_argument(
        "--run-refresh",
        action="store_true",
        help="Ejecuta refresh al final del runner. Si no se indica, usa MP_RUN_REFRESH del .env.",
    )
    parser.add_argument(
        "--refresh-limit",
        type=int,
        default=None,
        help="Cantidad maxima de licitaciones a refrescar. Si no se indica, usa MP_REFRESH_LIMIT del .env.",
    )
    parser.add_argument(
        "--refresh-timeout",
        type=int,
        default=None,
        help="Timeout por request en refresh. Si no se indica, usa MP_REFRESH_TIMEOUT del .env.",
    )
    parser.add_argument(
        "--refresh-retries",
        type=int,
        default=None,
        help="Reintentos por codigo en refresh. Si no se indica, usa MP_REFRESH_MAX_RETRIES del .env.",
    )
    parser.add_argument(
        "--refresh-backoff-seconds",
        type=float,
        default=None,
        help="Backoff base entre reintentos de refresh. Si no se indica, usa MP_REFRESH_BACKOFF_SECONDS del .env.",
    )
    parser.add_argument(
        "--refresh-sleep-sec",
        type=float,
        default=None,
        help="Pausa entre codigos refrescados. Si no se indica, usa MP_REFRESH_SLEEP_SEC del .env.",
    )
    parser.add_argument(
        "--refresh-force-terminal-awards",
        action="store_true",
        help="Fuerza refresh de terminales si falta adjudicacion, ignorando el .env.",
    )
    parser.add_argument(
        "--refresh-only-never-refreshed",
        action="store_true",
        help="Refresca solo licitaciones sin refresh previo. Si no se indica, usa MP_REFRESH_ONLY_NEVER_REFRESHED del .env.",
    )
    parser.add_argument(
        "--run-manual-review",
        action="store_true",
        help="Aplica revisión manual de transporte y reconstruye el master core. Si no se indica, usa MP_RUN_TRANSPORT_MANUAL_REVIEW del .env.",
    )
    parser.add_argument(
        "--manual-review-file",
        type=Path,
        default=None,
        help="CSV de revisión manual de transporte.",
    )
    parser.add_argument(
        "--manual-review-summary-file",
        type=Path,
        default=None,
        help="JSON resumen de la revisión manual.",
    )
    parser.add_argument(
        "--transport-core-master-path",
        type=Path,
        default=None,
        help="Ruta del master core reconstruido con revisión manual.",
    )
    parser.add_argument(
        "--run-analytics",
        action="store_true",
        help="Genera la capa analitica derivada al final del runner. Si no se indica, usa MP_RUN_ANALYTICS del .env.",
    )
    parser.add_argument(
        "--analytics-output-dir",
        type=Path,
        default=None,
        help="Directorio de salida para la capa analitica.",
    )
    parser.add_argument(
        "--run-quality",
        action="store_true",
        help="Ejecuta quality check del transport master. Si no se indica, usa MP_RUN_QUALITY_CHECK del .env.",
    )
    parser.add_argument(
        "--quality-output-dir",
        type=Path,
        default=None,
        help="Directorio de salida para reportes de calidad.",
    )
    parser.add_argument(
        "--run-serving",
        action="store_true",
        help="Genera la capa de serving derivada al final del runner. Si no se indica, usa MP_RUN_SERVING del .env.",
    )
    parser.add_argument(
        "--serving-output-dir",
        type=Path,
        default=None,
        help="Directorio de salida para artefactos de serving.",
    )
    parser.add_argument(
        "--no-sync-derived-after-master-change",
        action="store_true",
        help="Desactiva la sincronizacion automatica de analytics, quality y serving cuando cambie el master.",
    )
    args = parser.parse_args()

    run_transform_runner(
        raw_pattern=args.raw_pattern,
        overwrite=args.overwrite,
        min_score=args.min_score,
        enrich_limit=args.enrich_limit,
        enrich_only_errors=args.enrich_only_errors,
        enrich_max_attempts_per_code=args.enrich_max_attempts_per_code,
        enrich_sleep_sec=args.enrich_sleep_sec,
        enrich_pause_every=args.enrich_pause_every,
        enrich_pause_seconds=args.enrich_pause_seconds,
        run_refresh=True if args.run_refresh else None,
        refresh_limit=args.refresh_limit,
        refresh_timeout=args.refresh_timeout,
        refresh_retries=args.refresh_retries,
        refresh_backoff_seconds=args.refresh_backoff_seconds,
        refresh_sleep_sec=args.refresh_sleep_sec,
        refresh_force_terminal_awards=True if args.refresh_force_terminal_awards else None,
        refresh_only_never_refreshed=True if args.refresh_only_never_refreshed else None,
        run_manual_review=True if args.run_manual_review else None,
        manual_review_file=args.manual_review_file,
        manual_review_summary_file=args.manual_review_summary_file,
        transport_core_master_path=args.transport_core_master_path,
        run_analytics=True if args.run_analytics else None,
        analytics_output_dir=args.analytics_output_dir,
        run_quality=True if args.run_quality else None,
        quality_output_dir=args.quality_output_dir,
        run_serving=True if args.run_serving else None,
        serving_output_dir=args.serving_output_dir,
        sync_derived_after_master_change=False if args.no_sync_derived_after_master_change else None,
    )


if __name__ == "__main__":
    main()
