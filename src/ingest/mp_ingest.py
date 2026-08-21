# src/ingest/mp_ingest.py

import json
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

BASE_URL = "https://api.mercadopublico.cl/servicios/v1/publico/licitaciones.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("MP_API_KEY", "").strip().strip('"').strip("'")
if not API_KEY:
    raise ValueError(f"No se encontro MP_API_KEY valido en {ENV_PATH}")

DEFAULT_ESTADOS = ["5", "6", "7", "8", "18", "19"]
DEFAULT_START_DAY = int(os.getenv("START_DAY", "1"))
DEFAULT_END_DAY = int(os.getenv("END_DAY", "90"))
QUERY_MODE = os.getenv("MP_QUERY_MODE", "day").strip().lower()
SKIP_EXISTING_DAYS = os.getenv("MP_SKIP_EXISTING_DAYS", "true").strip().lower() in {
    "1", "true", "yes", "si"
}
MAX_RETRIES = int(os.getenv("MP_MAX_RETRIES", "5"))
TIMEOUT = int(os.getenv("MP_TIMEOUT", "30"))
SLEEP_BETWEEN_REQUESTS = float(os.getenv("MP_SLEEP_BETWEEN_REQUESTS", "1.5"))
BACKOFF_BASE_SECONDS = float(os.getenv("MP_BACKOFF_BASE_SECONDS", "2.0"))
BACKOFF_MAX_SECONDS = float(os.getenv("MP_BACKOFF_MAX_SECONDS", "90.0"))
JITTER_SECONDS = float(os.getenv("MP_JITTER_SECONDS", "0.75"))
COOLDOWN_AFTER_FAILURES = int(os.getenv("MP_COOLDOWN_AFTER_FAILURES", "3"))
COOLDOWN_SECONDS = float(os.getenv("MP_COOLDOWN_SECONDS", "60.0"))

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "TransData/0.1 MercadoPublico ingest",
}

ESTADO_ALIASES = {
    "publicada": "5",
    "cerrada": "6",
    "desierta": "7",
    "adjudicada": "8",
    "revocada": "18",
    "suspendida": "19",
    "todos": "todos",
}


def get_chile_now():
    return datetime.now()


def format_mp_date(days_ago):
    target_date = get_chile_now() - timedelta(days=days_ago)
    return target_date.strftime("%d%m%Y")


def normalize_estado_value(value):
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if not normalized:
        return None

    return ESTADO_ALIASES.get(normalized, normalized)


def normalize_estados(estados_env):
    if not estados_env:
        return DEFAULT_ESTADOS

    estados = []
    for raw_value in str(estados_env).split(","):
        normalized = normalize_estado_value(raw_value)
        if normalized:
            estados.append(normalized)

    return estados if estados else DEFAULT_ESTADOS


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def truncate_text(value, max_len=500):
    if value is None:
        return None

    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if len(text) <= max_len:
        return text

    return text[:max_len] + "...[truncated]"


def sleep_with_jitter(base_seconds):
    wait_seconds = max(0.0, float(base_seconds))
    if JITTER_SECONDS > 0:
        wait_seconds += random.uniform(0, JITTER_SECONDS)

    if wait_seconds > 0:
        time.sleep(wait_seconds)


def calculate_retry_wait(attempt):
    wait_seconds = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1))
    wait_seconds = min(wait_seconds, BACKOFF_MAX_SECONDS)

    if JITTER_SECONDS > 0:
        wait_seconds += random.uniform(0, JITTER_SECONDS)

    return wait_seconds


def extract_listado(data):
    if not isinstance(data, dict):
        return []

    listado = data.get("Listado", [])
    if isinstance(listado, list):
        return listado

    return []


def build_queries(start_day, end_day, estados, query_mode):
    queries = []

    for days_ago in range(start_day, end_day + 1):
        fecha = format_mp_date(days_ago)

        if query_mode == "day":
            queries.append({
                "fecha_consulta": fecha,
                "days_ago": days_ago,
                "estado_consulta": None,
                "query_mode": "day",
                "params": {
                    "fecha": fecha,
                    "ticket": API_KEY,
                },
            })
            continue

        if query_mode == "day_state":
            for estado in estados:
                queries.append({
                    "fecha_consulta": fecha,
                    "days_ago": days_ago,
                    "estado_consulta": estado,
                    "query_mode": "day_state",
                    "params": {
                        "fecha": fecha,
                        "estado": str(estado),
                        "ticket": API_KEY,
                    },
                })
            continue

        raise ValueError("MP_QUERY_MODE debe ser 'day' o 'day_state'")

    return queries


def list_raw_files(raw_dir=RAW_DIR):
    return sorted(Path(raw_dir).glob("mp_raw_*.json"), key=lambda p: p.stat().st_mtime)


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_query_key(fecha_consulta, query_mode, estado_consulta=None):
    return (
        str(fecha_consulta),
        str(query_mode),
        None if estado_consulta is None else str(estado_consulta),
    )


def discover_ingest_coverage(raw_dir=RAW_DIR):
    coverage = {
        "success_keys": set(),
        "failed_keys": set(),
        "raw_files": [],
    }

    for raw_path in list_raw_files(raw_dir):
        try:
            payload = load_json(raw_path)
        except Exception:
            continue

        coverage["raw_files"].append(raw_path.name)

        for result in payload.get("results", []):
            fecha_consulta = result.get("fecha_consulta")
            query_mode = result.get("query_mode") or "day_state"
            estado_consulta = result.get("estado_consulta")

            if not fecha_consulta:
                continue

            coverage["success_keys"].add(
                build_query_key(fecha_consulta, query_mode, estado_consulta)
            )

        for failed in payload.get("failed_queries", []):
            fecha_consulta = failed.get("fecha_consulta")
            query_mode = failed.get("query_mode") or "day_state"
            estado_consulta = failed.get("estado_consulta")

            if not fecha_consulta:
                continue

            coverage["failed_keys"].add(
                build_query_key(fecha_consulta, query_mode, estado_consulta)
            )

    return coverage


def filter_queries_against_coverage(queries, coverage):
    executable = []
    skipped = []
    success_keys = coverage.get("success_keys", set())

    for query in queries:
        query_key = build_query_key(
            query["fecha_consulta"],
            query["query_mode"],
            query["estado_consulta"],
        )

        if query_key in success_keys:
            skipped.append({
                "fecha_consulta": query["fecha_consulta"],
                "days_ago": query["days_ago"],
                "estado_consulta": query["estado_consulta"],
                "query_mode": query["query_mode"],
                "motivo": "already_ingested_successfully",
            })
        else:
            executable.append(query)

    return executable, skipped


def request_with_retries(session, params, max_retries=MAX_RETRIES, timeout=TIMEOUT):
    last_status_code = None
    last_error = None
    last_response_snippet = None

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(BASE_URL, params=params, timeout=timeout)
            last_status_code = response.status_code
            last_response_snippet = truncate_text(response.text)

            if response.status_code == 200:
                try:
                    return {
                        "status_code": 200,
                        "data": response.json(),
                        "error_type": None,
                        "attempts": attempt,
                        "response_snippet": None,
                    }
                except Exception as e:
                    return {
                        "status_code": 200,
                        "data": None,
                        "error_type": "invalid_json",
                        "attempts": attempt,
                        "last_error": str(e),
                        "response_snippet": last_response_snippet,
                    }

            if response.status_code == 203:
                try:
                    data = response.json()
                except Exception:
                    data = None

                return {
                    "status_code": 203,
                    "data": data,
                    "error_type": "non_authoritative",
                    "attempts": attempt,
                    "response_snippet": last_response_snippet,
                }

            if response.status_code in [429, 500, 502, 503, 504]:
                wait_seconds = calculate_retry_wait(attempt)
                print(
                    f"[WARN] Status {response.status_code} en intento "
                    f"{attempt}/{max_retries}. Reintento en {wait_seconds:.1f}s"
                )
                time.sleep(wait_seconds)
                continue

            try:
                response_data = response.json()
            except Exception:
                response_data = None

            return {
                "status_code": response.status_code,
                "data": response_data,
                "error_type": "non_retryable_status",
                "attempts": attempt,
                "response_snippet": last_response_snippet,
            }

        except requests.RequestException as e:
            last_error = str(e)
            wait_seconds = calculate_retry_wait(attempt)
            print(
                f"[WARN] Error de red en intento {attempt}/{max_retries}: "
                f"{e}. Reintento en {wait_seconds:.1f}s"
            )
            time.sleep(wait_seconds)

    return {
        "status_code": last_status_code,
        "data": None,
        "error_type": "request_failed",
        "attempts": max_retries,
        "last_error": last_error,
        "response_snippet": last_response_snippet,
    }


def run_ingest(
    start_day=DEFAULT_START_DAY,
    end_day=DEFAULT_END_DAY,
    estados=None,
    query_mode=QUERY_MODE,
    skip_existing_days=SKIP_EXISTING_DAYS,
):
    if estados is None:
        estados = DEFAULT_ESTADOS

    if start_day < 1:
        raise ValueError("START_DAY debe ser >= 1")

    if end_day < start_day:
        raise ValueError("END_DAY debe ser >= START_DAY")

    estados = [str(x) for x in estados]
    queries = build_queries(start_day, end_day, estados, query_mode)
    coverage = discover_ingest_coverage() if skip_existing_days else None
    skipped_existing_queries = []

    if coverage is not None:
        queries, skipped_existing_queries = filter_queries_against_coverage(queries, coverage)

    print("\n[INFO] Iniciando ingest de MercadoPublico...")
    print(f"[INFO] .env cargado desde: {ENV_PATH}")
    print(f"[INFO] Query mode: {query_mode}")
    print(f"[INFO] Ventana temporal: dias {start_day} a {end_day}")
    print(f"[INFO] Estados configurados: {estados}")
    print(f"[INFO] Skip existing days: {skip_existing_days}")
    print(f"[INFO] Total de consultas esperadas: {len(queries)}")
    print(f"[INFO] Consultas omitidas por cobertura previa: {len(skipped_existing_queries)}")

    results = []
    failed_queries = []

    total_queries = 0
    total_failed_queries = 0
    total_successful_queries = 0
    total_empty_queries = 0
    total_records_found = 0
    total_http_ok_queries = 0
    consecutive_failed_queries = 0

    started_at = datetime.now().isoformat()

    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)

    try:
        for query in queries:
            total_queries += 1
            fecha = query["fecha_consulta"]
            estado = query["estado_consulta"]

            print(
                f"\n[INFO] Consulta {total_queries}/{len(queries)}: "
                f"fecha={fecha} estado={estado} mode={query['query_mode']}"
            )

            response_info = request_with_retries(
                session=session,
                params=query["params"],
            )

            status_code = response_info.get("status_code")
            data = response_info.get("data")
            error_type = response_info.get("error_type")
            attempts = response_info.get("attempts")
            response_snippet = response_info.get("response_snippet")
            last_error = response_info.get("last_error")

            if data is None:
                total_failed_queries += 1
                consecutive_failed_queries += 1
                failed_queries.append({
                    "fecha_consulta": fecha,
                    "days_ago": query["days_ago"],
                    "estado_consulta": estado,
                    "query_mode": query["query_mode"],
                    "http_status": status_code,
                    "motivo": error_type,
                    "attempts": attempts,
                    "last_error": last_error,
                    "response_snippet": response_snippet,
                    "params": {
                        k: v for k, v in query["params"].items() if k != "ticket"
                    },
                })

                if (
                    COOLDOWN_AFTER_FAILURES > 0
                    and consecutive_failed_queries % COOLDOWN_AFTER_FAILURES == 0
                ):
                    print(
                        f"[WARN] {consecutive_failed_queries} fallas consecutivas. "
                        f"Cooldown de {COOLDOWN_SECONDS:.1f}s."
                    )
                    sleep_with_jitter(COOLDOWN_SECONDS)

                sleep_with_jitter(SLEEP_BETWEEN_REQUESTS)
                continue

            if isinstance(data, dict) and data.get("Mensaje") == "Ticket no válido.":
                total_failed_queries += 1
                consecutive_failed_queries += 1
                failed_queries.append({
                    "fecha_consulta": fecha,
                    "days_ago": query["days_ago"],
                    "estado_consulta": estado,
                    "query_mode": query["query_mode"],
                    "http_status": status_code,
                    "motivo": "invalid_ticket",
                    "attempts": attempts,
                    "last_error": last_error,
                    "response_snippet": response_snippet,
                    "response": data,
                    "params": {
                        k: v for k, v in query["params"].items() if k != "ticket"
                    },
                })

                print("[ERROR] La API respondio 'Ticket no valido.'")
                sleep_with_jitter(SLEEP_BETWEEN_REQUESTS)
                continue

            consecutive_failed_queries = 0
            total_http_ok_queries += 1

            listado = extract_listado(data)
            cantidad_reportada = safe_int(data.get("Cantidad", 0), default=len(listado))
            cantidad_real = len(listado)

            if cantidad_real == 0:
                total_empty_queries += 1
            else:
                total_successful_queries += 1

            total_records_found += cantidad_real

            results.append({
                "fecha_consulta": fecha,
                "days_ago": query["days_ago"],
                "estado_consulta": estado,
                "query_mode": query["query_mode"],
                "http_status": status_code,
                "attempts": attempts,
                "cantidad_reportada": cantidad_reportada,
                "cantidad_real_listado": cantidad_real,
                "params": {
                    k: v for k, v in query["params"].items() if k != "ticket"
                },
                "response": data,
            })

            sleep_with_jitter(SLEEP_BETWEEN_REQUESTS)

    finally:
        session.close()

    ended_at = datetime.now().isoformat()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output = {
        "metadata": {
            "source": "MercadoPublico",
            "base_url": BASE_URL,
            "project_root": str(PROJECT_ROOT),
            "env_path": str(ENV_PATH),
            "generated_at": ended_at,
            "started_at": started_at,
            "ended_at": ended_at,
            "start_day": start_day,
            "end_day": end_day,
            "total_days": end_day - start_day + 1,
            "query_mode": query_mode,
            "estados_configurados": estados,
            "skip_existing_days": skip_existing_days,
            "skipped_existing_queries": len(skipped_existing_queries),
            "total_expected_queries": len(queries),
            "total_queries_executed": total_queries,
            "total_http_ok_queries": total_http_ok_queries,
            "total_successful_queries": total_successful_queries,
            "total_empty_queries": total_empty_queries,
            "total_failed_queries": total_failed_queries,
            "total_records_found": total_records_found,
            "max_retries": MAX_RETRIES,
            "timeout_seconds": TIMEOUT,
            "sleep_between_requests": SLEEP_BETWEEN_REQUESTS,
            "backoff_base_seconds": BACKOFF_BASE_SECONDS,
            "backoff_max_seconds": BACKOFF_MAX_SECONDS,
            "jitter_seconds": JITTER_SECONDS,
            "cooldown_after_failures": COOLDOWN_AFTER_FAILURES,
            "cooldown_seconds": COOLDOWN_SECONDS,
        },
        "skipped_existing_queries": skipped_existing_queries,
        "failed_queries": failed_queries,
        "results": results,
    }

    output_filename = f"mp_raw_{start_day}_{end_day}_{timestamp}.json"
    output_path = RAW_DIR / output_filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n[INFO] Ingest finalizado.")
    print(f"[INFO] Archivo guardado en: {output_path}")
    print(f"[INFO] Consultas ejecutadas: {total_queries}/{len(queries)}")
    print(f"[INFO] Consultas HTTP OK: {total_http_ok_queries}")
    print(f"[INFO] Consultas con datos: {total_successful_queries}")
    print(f"[INFO] Consultas vacias: {total_empty_queries}")
    print(f"[INFO] Consultas fallidas: {total_failed_queries}")
    print(f"[INFO] Registros encontrados: {total_records_found}")

    return output_path


if __name__ == "__main__":
    estados = normalize_estados(os.getenv("ESTADOS"))
    start_day = int(os.getenv("START_DAY", "1"))
    end_day = int(os.getenv("END_DAY", "90"))

    run_ingest(
        start_day=start_day,
        end_day=end_day,
        estados=estados,
        query_mode=QUERY_MODE,
    )
