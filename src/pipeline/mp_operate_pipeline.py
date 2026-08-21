from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
TRANSFORM_DIR = ROOT / "src" / "transform"
PIPELINE_REPORTS_DIR = ROOT / "data" / "reports" / "operations"

import sys

if str(TRANSFORM_DIR) not in sys.path:
    sys.path.insert(0, str(TRANSFORM_DIR))

from mp_pipeline_health import build_health_report, write_health_report  # noqa: E402
from mp_transform_runner import run_transform_runner  # noqa: E402


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def env_int(name: str, default: int) -> int:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return int(value) if value else default


def env_float(name: str, default: float) -> float:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return float(value) if value else default


def env_bool(name: str, default: bool) -> bool:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'").lower()
    if value in {"true", "1", "si", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return default


def env_str(name: str, default: str) -> str:
    load_env()
    raw = os.getenv(name, "")
    value = str(raw).strip().strip('"').strip("'")
    return value if value else default


def write_operation_summary(summary: dict) -> Path:
    PIPELINE_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = PIPELINE_REPORTS_DIR / f"mp_operate_pipeline_summary_{timestamp}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return path


def resolve_mode_defaults(mode: str) -> dict:
    normalized = mode.strip().lower()
    if normalized == "daily":
        return {
            "refresh_limit": env_int("MP_DAILY_REFRESH_LIMIT", 300),
            "run_refresh": env_bool("MP_DAILY_RUN_REFRESH", True),
            "run_health": env_bool("MP_DAILY_RUN_HEALTH", env_bool("MP_OPERATION_RUN_HEALTH", True)),
            "refresh_only_never_refreshed": env_bool("MP_DAILY_REFRESH_ONLY_NEVER_REFRESHED", False),
        }
    if normalized == "weekly":
        return {
            "refresh_limit": env_int("MP_WEEKLY_REFRESH_LIMIT", 1000),
            "run_refresh": env_bool("MP_WEEKLY_RUN_REFRESH", True),
            "run_health": env_bool("MP_WEEKLY_RUN_HEALTH", env_bool("MP_OPERATION_RUN_HEALTH", True)),
            "refresh_only_never_refreshed": env_bool("MP_WEEKLY_REFRESH_ONLY_NEVER_REFRESHED", False),
        }
    raise ValueError(f"Modo operativo no soportado: {mode}")


def run_operational_cycle(
    mode: str,
    raw_pattern: str = "mp_raw_*.json",
    min_score: int = 3,
    enrich_limit: int | None = None,
    refresh_limit: int | None = None,
    refresh_sleep_sec: float | None = None,
    run_refresh: bool | None = None,
    refresh_only_never_refreshed: bool | None = None,
    run_health: bool | None = None,
) -> Path:
    started_at = datetime.now().isoformat()
    defaults = resolve_mode_defaults(mode)

    if run_refresh is None:
        run_refresh = defaults["run_refresh"]
    if refresh_limit is None:
        refresh_limit = defaults["refresh_limit"]
    if refresh_only_never_refreshed is None:
        refresh_only_never_refreshed = defaults["refresh_only_never_refreshed"]
    if refresh_sleep_sec is None:
        refresh_sleep_sec = env_float(
            "MP_OPERATION_REFRESH_SLEEP_SEC",
            env_float("MP_REFRESH_SLEEP_SEC", 0.6),
        )
    if enrich_limit is None:
        enrich_limit = env_int(
            "MP_OPERATION_ENRICH_LIMIT",
            env_int("MP_ENRICH_LIMIT", 10000),
        )
    if run_health is None:
        run_health = defaults["run_health"]

    print("[INFO] Iniciando ciclo operativo del pipeline...")
    print(f"[INFO] Modo: {mode}")
    print(f"[INFO] Raw pattern: {raw_pattern}")
    print(f"[INFO] Min score transporte: {min_score}")
    print(f"[INFO] Refresh habilitado: {run_refresh}")
    print(f"[INFO] Refresh limit: {refresh_limit}")
    print(f"[INFO] Refresh solo nunca refrescadas: {refresh_only_never_refreshed}")
    print(f"[INFO] Enrich limit: {enrich_limit}")
    print(f"[INFO] Health report habilitado: {run_health}")

    runner_summary_path = run_transform_runner(
        raw_pattern=raw_pattern,
        overwrite=False,
        min_score=min_score,
        enrich_limit=enrich_limit,
        run_refresh=run_refresh,
        refresh_limit=refresh_limit,
        refresh_sleep_sec=refresh_sleep_sec,
        refresh_only_never_refreshed=refresh_only_never_refreshed,
        run_analytics=False,
        run_quality=False,
        run_serving=False,
        sync_derived_after_master_change=True,
    )

    health_report_path = None
    if run_health:
        report = build_health_report()
        health_report_path = write_health_report(report)
        print(f"[INFO] Health report generado: {health_report_path}")

    summary = {
        "metadata": {
            "type": "operate_pipeline_summary",
            "mode": mode,
            "started_at": started_at,
            "ended_at": datetime.now().isoformat(),
        },
        "settings": {
            "raw_pattern": raw_pattern,
            "min_score": min_score,
            "enrich_limit": enrich_limit,
            "run_refresh": run_refresh,
            "refresh_limit": refresh_limit,
            "refresh_sleep_sec": refresh_sleep_sec,
            "refresh_only_never_refreshed": refresh_only_never_refreshed,
            "run_health": run_health,
        },
        "artifacts": {
            "runner_summary_path": str(runner_summary_path),
            "health_report_path": str(health_report_path) if health_report_path else None,
        },
    }
    summary_path = write_operation_summary(summary)

    print("[OK] Ciclo operativo finalizado.")
    print(f"[INFO] Resumen operativo: {summary_path}")
    return summary_path


def main():
    env_mode = env_str("MP_OPERATION_MODE", "daily").strip().lower()
    env_raw_pattern = env_str("MP_OPERATION_RAW_PATTERN", "mp_raw_*.json")
    env_min_score = env_int("MP_OPERATION_MIN_SCORE", 3)

    parser = argparse.ArgumentParser(
        description="Ejecuta un ciclo operativo diario o semanal del pipeline de TransData."
    )
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly"],
        default=env_mode,
        help="Preset operativo a ejecutar. Si no se indica, usa MP_OPERATION_MODE del .env.",
    )
    parser.add_argument(
        "--raw-pattern",
        default=env_raw_pattern,
        help="Patron glob para raws a procesar. Si no se indica, usa MP_OPERATION_RAW_PATTERN del .env.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=env_min_score,
        help="Puntaje minimo para clasificar transporte. Si no se indica, usa MP_OPERATION_MIN_SCORE del .env.",
    )
    parser.add_argument(
        "--enrich-limit",
        type=int,
        default=None,
        help="Limite de enrich para esta corrida. Si no se indica, usa MP_ENRICH_LIMIT del .env.",
    )
    parser.add_argument(
        "--refresh-limit",
        type=int,
        default=None,
        help="Limite de refresh para esta corrida. Si no se indica, usa el preset del modo.",
    )
    parser.add_argument(
        "--refresh-sleep-sec",
        type=float,
        default=None,
        help="Pausa entre codigos refrescados.",
    )
    parser.add_argument(
        "--refresh-only-never-refreshed",
        action="store_true",
        help="Refresca solo licitaciones sin refresh previo. Si no se indica, usa el preset del modo o el .env.",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Desactiva refresh para esta corrida.",
    )
    parser.add_argument(
        "--no-health",
        action="store_true",
        help="No genera health report al finalizar.",
    )
    args = parser.parse_args()

    run_operational_cycle(
        mode=args.mode,
        raw_pattern=args.raw_pattern,
        min_score=args.min_score,
        enrich_limit=args.enrich_limit,
        refresh_limit=args.refresh_limit,
        refresh_sleep_sec=args.refresh_sleep_sec,
        run_refresh=False if args.no_refresh else None,
        refresh_only_never_refreshed=True if args.refresh_only_never_refreshed else None,
        run_health=not args.no_health,
    )


if __name__ == "__main__":
    main()
