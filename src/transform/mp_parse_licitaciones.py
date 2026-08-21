import json
import re
import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"


# =========================================================
# Utilidades base
# =========================================================
def find_latest_raw():
    files = sorted(RAW_DIR.glob("mp_raw_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos raw en: {RAW_DIR}")
    return files[0]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def now_str():
    return pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_get(d, *keys, default=None):
    current = d
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def parse_timestamp_from_filename(filename):
    m = re.search(r"(\d{8}_\d{6})", filename)
    return m.group(1) if m else None


def parse_range_from_filename(filename):
    """
    Intenta extraer start_day y end_day desde nombres tipo:
    - mp_raw_15_45_20260403_120000.json
    - mp_raw_dias_15_45_20260403_120000.json
    - mp_raw_15_45.json
    - mp_raw_dias_15_45.json
    """
    patterns = [
        r"mp_raw_(\d+)_(\d+)_\d{8}_\d{6}\.json$",
        r"mp_raw_dias_(\d+)_(\d+)_\d{8}_\d{6}\.json$",
        r"mp_raw_(\d+)_(\d+)\.json$",
        r"mp_raw_dias_(\d+)_(\d+)\.json$",
    ]

    for pattern in patterns:
        m = re.search(pattern, filename)
        if m:
            return int(m.group(1)), int(m.group(2))

    return None, None


def normalize_fecha_consulta(value):
    """
    Convierte fechas tipo:
    - 02042026
    - 02-04-2026
    - 2026-04-02
    a formato YYYY-MM-DD cuando sea posible.
    """
    if value is None:
        return None

    s = str(value).strip()

    # ddmmyyyy
    if re.fullmatch(r"\d{8}", s):
        try:
            return pd.to_datetime(s, format="%d%m%Y", errors="coerce").strftime("%Y-%m-%d")
        except Exception:
            return None

    # otros formatos comunes
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    if pd.isna(dt):
        return None

    return dt.strftime("%Y-%m-%d")


# =========================================================
# Metadata del raw / ingest
# =========================================================
def extract_ingest_metadata(raw_data, raw_path):
    """
    Intenta obtener metadata desde:
    - raw_data["metadata"]
    - raw_data["meta"]
    - nombre del archivo
    """
    metadata = raw_data.get("metadata", {}) if isinstance(raw_data, dict) else {}
    meta = raw_data.get("meta", {}) if isinstance(raw_data, dict) else {}

    start_day = (
        metadata.get("start_day")
        or metadata.get("day_start")
        or meta.get("start_day")
        or meta.get("day_start")
    )

    end_day = (
        metadata.get("end_day")
        or metadata.get("day_end")
        or meta.get("end_day")
        or meta.get("day_end")
    )

    if start_day is None or end_day is None:
        file_start, file_end = parse_range_from_filename(raw_path.name)
        start_day = start_day if start_day is not None else file_start
        end_day = end_day if end_day is not None else file_end

    ingest_timestamp = (
        metadata.get("timestamp")
        or metadata.get("created_at")
        or meta.get("timestamp")
        or meta.get("created_at")
        or parse_timestamp_from_filename(raw_path.name)
    )

    return {
        "raw_file": raw_path.name,
        "ingest_start_day": start_day,
        "ingest_end_day": end_day,
        "ingest_timestamp": ingest_timestamp,
    }


# =========================================================
# Descubrimiento de bloques de consulta
# =========================================================
def looks_like_query_block(d):
    """
    Detecta si un dict se parece a un bloque de consulta del ingest.
    """
    if not isinstance(d, dict):
        return False

    possible_fecha = (
        "fecha" in d
        or "Fecha" in d
        or "fecha_consulta" in d
        or "FechaConsulta" in d
    )

    possible_estado = (
        "estado" in d
        or "Estado" in d
        or "codigo_estado" in d
        or "CodigoEstado" in d
        or "estado_consultado" in d
    )

    has_listado_direct = isinstance(d.get("Listado"), list)
    has_respuesta_listado = isinstance(safe_get(d, "respuesta", "Listado"), list)
    has_response_listado = isinstance(safe_get(d, "response", "Listado"), list)
    has_data_listado = isinstance(safe_get(d, "data", "Listado"), list)

    has_some_listado = (
        has_listado_direct
        or has_respuesta_listado
        or has_response_listado
        or has_data_listado
    )

    return has_some_listado or (possible_fecha and possible_estado)


def extract_query_blocks(obj):
    """
    Recorre recursivamente el JSON y devuelve todos los bloques
    que parecen consultas del ingest.
    """
    found = []

    if isinstance(obj, dict):
        if looks_like_query_block(obj):
            found.append(obj)

        for value in obj.values():
            found.extend(extract_query_blocks(value))

    elif isinstance(obj, list):
        for item in obj:
            found.extend(extract_query_blocks(item))

    return found


def get_query_context(block):
    fecha_consulta = (
        block.get("fecha")
        or block.get("Fecha")
        or block.get("fecha_consulta")
        or block.get("FechaConsulta")
    )

    estado_consultado = (
        block.get("estado")
        or block.get("Estado")
        or block.get("codigo_estado")
        or block.get("CodigoEstado")
        or block.get("estado_consultado")
    )

    return {
        "fecha_consulta": normalize_fecha_consulta(fecha_consulta),
        "estado_consultado": estado_consultado,
    }


def get_query_listado(block):
    """
    Extrae el Listado desde distintas posibles estructuras.
    """
    candidates = [
        block.get("Listado"),
        safe_get(block, "respuesta", "Listado"),
        safe_get(block, "response", "Listado"),
        safe_get(block, "data", "Listado"),
        safe_get(block, "respuesta", "data", "Listado"),
        safe_get(block, "response", "data", "Listado"),
    ]

    for c in candidates:
        if isinstance(c, list):
            return c

    return []


# =========================================================
# Normalización de licitaciones
# =========================================================
def normalize_licitacion(item, query_ctx, ingest_meta, parse_timestamp):
    estado_actual = (
        item.get("CodigoEstado")
        or item.get("Estado")
        or item.get("estado")
    )

    row = {
        # Identidad
        "codigo_licitacion": item.get("CodigoExterno") or item.get("codigo_licitacion"),
        "nombre_licitacion": item.get("Nombre") or item.get("nombre_licitacion"),
        "descripcion": item.get("Descripcion") or item.get("descripcion"),

        # Estados
        "estado_actual": estado_actual,
        "estado_consultado": query_ctx.get("estado_consultado"),

        # Fechas licitación
        "fecha_publicacion": item.get("FechaCreacion") or item.get("fecha_publicacion"),
        "fecha_cierre": item.get("FechaCierre") or item.get("fecha_cierre"),
        "dias_publicacion": item.get("DiasCierreLicitacion") or item.get("dias_publicacion"),

        # Monto / moneda
        "moneda": item.get("Moneda") or item.get("moneda"),
        "monto_estimado": item.get("MontoEstimado") or item.get("monto_estimado"),

        # Comprador
        "comprador_nombre": safe_get(item, "Comprador", "NombreOrganismo"),
        "comprador_rut": safe_get(item, "Comprador", "RutUnidad"),
        "comprador_region": safe_get(item, "Comprador", "RegionUnidad"),
        "comprador_comuna": safe_get(item, "Comprador", "ComunaUnidad"),
        "unidad_nombre": safe_get(item, "Comprador", "NombreUnidad"),
        "region": safe_get(item, "Comprador", "RegionUnidad"),

        # Otros campos
        "tipo": item.get("Tipo") or item.get("tipo"),
        "etapas": item.get("Etapas") or item.get("etapas"),
        "url_acta": item.get("UrlActa") or item.get("url_acta"),
        "url_ficha": item.get("UrlFicha") or item.get("url_ficha"),

        # Contexto de consulta
        "fecha_consulta": query_ctx.get("fecha_consulta"),

        # Metadata ingest
        "raw_file": ingest_meta.get("raw_file"),
        "ingest_start_day": ingest_meta.get("ingest_start_day"),
        "ingest_end_day": ingest_meta.get("ingest_end_day"),
        "ingest_timestamp": ingest_meta.get("ingest_timestamp"),

        # Operativo
        "parse_timestamp": parse_timestamp,
        "registro_fuente": "ingest",
    }

    return row


# =========================================================
# DataFrame y deduplicación
# =========================================================
def add_operational_columns(df):
    if df.empty:
        return df

    # Cuenta cuántas veces aparece el código dentro del mismo raw parseado
    counts = df["codigo_licitacion"].value_counts(dropna=False).to_dict()

    df["duplicados_en_raw"] = df["codigo_licitacion"].map(counts).fillna(0).astype(int)
    df["es_duplicado_raw"] = df["duplicados_en_raw"] > 1

    return df


def prepare_dates(df):
    for col in ["fecha_publicacion", "fecha_cierre", "fecha_consulta"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def deduplicate_intelligently(df):
    """
    Deduplicación más inteligente:
    - score por cantidad de campos no nulos
    - prioridad a registros con fecha_consulta más reciente
    - prioridad a última aparición
    """
    if df.empty or "codigo_licitacion" not in df.columns:
        return df

    df = df.copy()

    # score de completitud
    df["_completitud_score"] = df.notna().sum(axis=1)

    # índice de aparición para romper empates
    df["_row_order"] = range(len(df))

    # para sort estable
    sort_cols = ["codigo_licitacion", "_completitud_score", "fecha_consulta", "_row_order"]
    ascending = [True, False, False, False]

    df = df.sort_values(by=sort_cols, ascending=ascending, na_position="last")

    # nos quedamos con el mejor por código
    df = df.drop_duplicates(subset=["codigo_licitacion"], keep="first")

    # limpiar auxiliares
    df = df.drop(columns=["_completitud_score", "_row_order"], errors="ignore")

    return df


def build_dataframe(raw_data, raw_path):
    parse_timestamp = now_str()
    ingest_meta = extract_ingest_metadata(raw_data, raw_path)

    query_blocks = extract_query_blocks(raw_data)

    registros = []

    # Si encontramos bloques de consulta, parseamos con contexto
    if query_blocks:
        for block in query_blocks:
            query_ctx = get_query_context(block)
            listado = get_query_listado(block)

            if not listado:
                continue

            for item in listado:
                if isinstance(item, dict):
                    registros.append(
                        normalize_licitacion(
                            item=item,
                            query_ctx=query_ctx,
                            ingest_meta=ingest_meta,
                            parse_timestamp=parse_timestamp,
                        )
                    )

    # Fallback: si por alguna razón no se detectaron bloques,
    # buscamos recursivamente cualquier Listado
    if not registros:
        listados = extract_all_listados(raw_data)

        for listado in listados:
            for item in listado:
                if isinstance(item, dict):
                    registros.append(
                        normalize_licitacion(
                            item=item,
                            query_ctx={"fecha_consulta": None, "estado_consultado": None},
                            ingest_meta=ingest_meta,
                            parse_timestamp=parse_timestamp,
                        )
                    )

    if not registros:
        raise ValueError("No se encontraron licitaciones válidas dentro del archivo raw.")

    df = pd.DataFrame(registros)

    df = add_operational_columns(df)
    df = prepare_dates(df)
    df = deduplicate_intelligently(df)

    # ultima_revision: queda lista para el refresh
    df["ultima_revision"] = now_str()

    return df


def extract_all_listados(obj):
    encontrados = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "Listado" and isinstance(v, list):
                encontrados.append(v)
            else:
                encontrados.extend(extract_all_listados(v))

    elif isinstance(obj, list):
        for item in obj:
            encontrados.extend(extract_all_listados(item))

    return encontrados


# =========================================================
# Salida
# =========================================================
def build_output_name(raw_path):
    start_day, end_day = parse_range_from_filename(raw_path.name)
    timestamp = parse_timestamp_from_filename(raw_path.name)

    if timestamp is None:
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")

    if start_day is not None and end_day is not None:
        return f"licitaciones_processed_{start_day}_{end_day}_{timestamp}.csv"

    return f"licitaciones_processed_{timestamp}.csv"


def build_empty_parse_summary(raw_data, raw_path, error_message):
    ingest_meta = extract_ingest_metadata(raw_data, raw_path)
    metadata = raw_data.get("metadata", {}) if isinstance(raw_data, dict) else {}
    failed_queries = raw_data.get("failed_queries", []) if isinstance(raw_data, dict) else []
    results = raw_data.get("results", []) if isinstance(raw_data, dict) else []

    return {
        "raw_file": raw_path.name,
        "status": "no_records",
        "message": error_message,
        "parsed_at": now_str(),
        "ingest_start_day": ingest_meta.get("ingest_start_day"),
        "ingest_end_day": ingest_meta.get("ingest_end_day"),
        "ingest_timestamp": ingest_meta.get("ingest_timestamp"),
        "raw_total_results_blocks": len(results) if isinstance(results, list) else None,
        "raw_failed_queries": len(failed_queries) if isinstance(failed_queries, list) else None,
        "raw_total_records_found": metadata.get("total_records_found"),
    }


def order_columns(df):
    preferred = [
        "codigo_licitacion",
        "nombre_licitacion",
        "descripcion",
        "estado_actual",
        "estado_consultado",
        "fecha_publicacion",
        "fecha_cierre",
        "dias_publicacion",
        "moneda",
        "monto_estimado",
        "comprador_nombre",
        "comprador_rut",
        "comprador_region",
        "comprador_comuna",
        "unidad_nombre",
        "region",
        "tipo",
        "etapas",
        "url_acta",
        "url_ficha",
        "fecha_consulta",
        "raw_file",
        "ingest_start_day",
        "ingest_end_day",
        "ingest_timestamp",
        "parse_timestamp",
        "ultima_revision",
        "registro_fuente",
        "duplicados_en_raw",
        "es_duplicado_raw",
    ]

    existing_preferred = [c for c in preferred if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_preferred]

    return df[existing_preferred + remaining]


def parse_raw_file(raw_path, output_dir=PROCESSED_DIR, overwrite=False):
    """
    Parsea un raw de MercadoPublico y escribe un CSV procesado.

    Retorna un dict pequeño para que el batch pueda decidir si el archivo
    fue procesado, saltado o si no contenia registros validos.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = Path(raw_path)
    output_path = output_dir / build_output_name(raw_path)

    if output_path.exists() and not overwrite:
        return {
            "raw_file": raw_path.name,
            "output_file": str(output_path),
            "status": "skipped_existing",
            "rows": None,
            "parsed_at": now_str(),
        }

    raw_data = load_json(raw_path)

    try:
        df = build_dataframe(raw_data, raw_path)
    except ValueError as e:
        summary = build_empty_parse_summary(raw_data, raw_path, str(e))
        summary["output_file"] = None
        summary["rows"] = 0
        return summary

    df = order_columns(df)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    return {
        "raw_file": raw_path.name,
        "output_file": str(output_path),
        "status": "processed",
        "rows": len(df),
        "columns": list(df.columns),
        "parsed_at": now_str(),
    }


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    parser = argparse.ArgumentParser(
        description="Parsea un archivo raw de MercadoPublico a CSV tabular."
    )
    parser.add_argument(
        "--raw-file",
        type=Path,
        default=None,
        help="Ruta al raw JSON. Si no se entrega, usa el raw mas reciente.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocesa aunque el CSV de salida ya exista.",
    )
    args = parser.parse_args()

    raw_path = args.raw_file or find_latest_raw()
    print(f"[INFO] Leyendo raw: {raw_path}")

    result = parse_raw_file(raw_path, output_dir=PROCESSED_DIR, overwrite=args.overwrite)

    if result["status"] == "processed":
        print(f"[OK] CSV procesado guardado en: {result['output_file']}")
        print(f"[INFO] Filas finales: {result['rows']}")
        print(f"[INFO] Columnas: {result['columns']}")
    elif result["status"] == "skipped_existing":
        print(f"[INFO] Ya existia output. Saltado: {result['output_file']}")
    else:
        print(f"[WARN] Raw sin registros procesables: {result['raw_file']}")
        print(f"[WARN] Motivo: {result['message']}")


if __name__ == "__main__":
    main()
