import argparse
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"
TRANSPORT_DIR = PROCESSED_DIR / "transport"

POSITIVE_RULES = [
    {"pattern": r"\btransporte de pasajeros\b", "score": 4, "label": "transporte_pasajeros"},
    {"pattern": r"\btraslado de pasajeros\b", "score": 4, "label": "traslado_pasajeros"},
    {"pattern": r"\bservicio de transporte(?: escolar)?\b", "score": 3, "label": "servicio_transporte"},
    {"pattern": r"\bmovilizacion de pasajeros\b", "score": 4, "label": "movilizacion_pasajeros"},
    {"pattern": r"\btransporte escolar\b", "score": 4, "label": "transporte_escolar"},
    {"pattern": r"\bbus(?:es)?\b", "score": 2, "label": "bus"},
    {"pattern": r"\bminibus(?:es)?\b", "score": 2, "label": "minibus"},
    {"pattern": r"\btransfer\b", "score": 2, "label": "transfer"},
    {"pattern": r"\bvan(?:es)?\b", "score": 2, "label": "van"},
    {"pattern": r"\bacercamiento\b", "score": 2, "label": "acercamiento"},
    {"pattern": r"\btraslado\b", "score": 2, "label": "traslado"},
]

PASSENGER_CONTEXT_RULES = [
    {"pattern": r"\bpasajeros?\b", "label": "ctx_pasajeros"},
    {"pattern": r"\bpersonas?\b", "label": "ctx_personas"},
    {"pattern": r"\bfuncionarios?\b", "label": "ctx_funcionarios"},
    {"pattern": r"\bestudiantes?\b", "label": "ctx_estudiantes"},
    {"pattern": r"\balumnos?\b", "label": "ctx_alumnos"},
    {"pattern": r"\bpacientes?\b", "label": "ctx_pacientes"},
    {"pattern": r"\bcomunidad educativa\b", "label": "ctx_comunidad_educativa"},
    {"pattern": r"\bpersonal\b", "label": "ctx_personal"},
    {"pattern": r"\bdocentes?\b", "label": "ctx_docentes"},
    {"pattern": r"\bapoderados?\b", "label": "ctx_apoderados"},
]

LAND_MODE_RULES = [
    {"pattern": r"\bbus(?:es)?\b", "label": "modo_bus"},
    {"pattern": r"\bminibus(?:es)?\b", "label": "modo_minibus"},
    {"pattern": r"\bvan(?:es)?\b", "label": "modo_van"},
    {"pattern": r"\bmini van\b", "label": "modo_minivan"},
    {"pattern": r"\btaxi\b", "label": "modo_taxi"},
    {"pattern": r"\bvehicul(?:o|os)\b", "label": "modo_vehiculo"},
    {"pattern": r"\bchofer\b", "label": "modo_chofer"},
    {"pattern": r"\bconductor\b", "label": "modo_conductor"},
    {"pattern": r"\bmoviles?\b", "label": "modo_moviles"},
    {"pattern": r"\bfurgon(?:es)?\b", "label": "modo_furgon"},
    {"pattern": r"\bstation wagon\b", "label": "modo_station_wagon"},
    {"pattern": r"\bsedan\b", "label": "modo_sedan"},
    {"pattern": r"\bcamioneta(?:s)?\b", "label": "modo_camioneta"},
]

STRONG_LAND_MODE_LABELS = {
    "modo_bus",
    "modo_minibus",
    "modo_van",
    "modo_minivan",
    "modo_taxi",
    "modo_furgon",
    "modo_station_wagon",
    "modo_sedan",
}

ACTIVITY_CONTEXT_RULES = [
    {"pattern": r"\bsalidas? pedagogic(?:a|as)\b", "label": "ctx_salidas_pedagogicas"},
    {"pattern": r"\bsalidas? extraescolares?\b", "label": "ctx_salidas_extraescolares"},
    {"pattern": r"\bsalidas? extracurriculares?\b", "label": "ctx_salidas_extracurriculares"},
    {"pattern": r"\bviajes? educativos?\b", "label": "ctx_viajes_educativos"},
    {"pattern": r"\bgira(?:s)? de estudio\b", "label": "ctx_gira_estudio"},
    {"pattern": r"\batenci[oó]n domiciliaria\b", "label": "ctx_atencion_domiciliaria"},
    {"pattern": r"\bvisitas? domiciliarias?\b", "label": "ctx_visitas_domiciliarias"},
    {"pattern": r"\bjardi[ní]n infantil\b", "label": "ctx_jardin_infantil"},
    {"pattern": r"\bsala cuna\b", "label": "ctx_sala_cuna"},
    {"pattern": r"\bapoyo escolar\b", "label": "ctx_apoyo_escolar"},
    {"pattern": r"\bcomunidad educativa\b", "label": "ctx_comunidad_educativa_actividad"},
    {"pattern": r"\badultos? mayores?\b", "label": "ctx_adultos_mayores"},
]

DOMAIN_CONTEXT_RULES = [
    {"pattern": r"\bslep\b", "label": "dom_slep"},
    {"pattern": r"\bescuel(?:a|as)\b", "label": "dom_escuela"},
    {"pattern": r"\bliceo\b", "label": "dom_liceo"},
    {"pattern": r"\bestablecimientos? educacionales?\b", "label": "dom_establecimientos_educacionales"},
    {"pattern": r"\beducaci[oó]n\b", "label": "dom_educacion"},
    {"pattern": r"\bjardi(?:n|nes) infantiles?\b", "label": "dom_jardin_infantil"},
    {"pattern": r"\bcentros? ceci\b", "label": "dom_ceci"},
    {"pattern": r"\bcentros? de salud\b", "label": "dom_centros_salud"},
    {"pattern": r"\batenci[oó]n primaria de salud\b", "label": "dom_aps"},
    {"pattern": r"\bsalud ocupacional\b", "label": "dom_salud_ocupacional"},
    {"pattern": r"\bcuidados paliativos?\b", "label": "dom_cuidados_paliativos"},
    {"pattern": r"\bred local de apoyos? y cuidados?\b", "label": "dom_red_cuidados"},
    {"pattern": r"\bchile crece contigo\b", "label": "dom_chile_crece_contigo"},
    {"pattern": r"\badulto mayor\b", "label": "dom_adulto_mayor"},
    {"pattern": r"\bdiscapacidad\b", "label": "dom_discapacidad"},
    {"pattern": r"\bdideco\b", "label": "dom_dideco"},
    {"pattern": r"\bprlac\b", "label": "dom_prlac"},
    {"pattern": r"\bfofar\b", "label": "dom_fofar"},
    {"pattern": r"\bfondo de farmacia\b", "label": "dom_farmacia"},
    {"pattern": r"\bprograma 4a7\b", "label": "dom_programa_4a7"},
    {"pattern": r"\bni[ñn]ez\b", "label": "dom_ninez"},
    {"pattern": r"\bsename\b", "label": "dom_sename"},
    {"pattern": r"\bdeudos?\b", "label": "dom_deudos"},
    {"pattern": r"\bactividades? acad[eé]micas?\b", "label": "dom_actividades_academicas"},
]

NEGATIVE_RULES = [
    {"pattern": r"\bpasajeros?\s+y\/?\s*carga\b", "score": -5, "label": "pasajeros_y_carga"},
    {"pattern": r"\bcarga\s+y\/?\s*pasajeros?\b", "score": -5, "label": "carga_y_pasajeros"},
    {"pattern": r"\btransporte de carga\b", "score": -5, "label": "transporte_carga"},
    {"pattern": r"\bflete(?:s)?\b", "score": -4, "label": "flete"},
    {"pattern": r"\bcamion(?:es)?\b", "score": -3, "label": "camion"},
    {"pattern": r"\bcamion aljibe\b", "score": -5, "label": "camion_aljibe"},
    {"pattern": r"\bgrua(?:s)?\b", "score": -4, "label": "grua"},
    {"pattern": r"\bresiduos?\b", "score": -4, "label": "residuos"},
    {"pattern": r"\bbasura\b", "score": -4, "label": "basura"},
    {"pattern": r"\bcarga\b", "score": -3, "label": "carga"},
    {"pattern": r"\bmudanza\b", "score": -4, "label": "mudanza"},
]

EXCLUSION_RULES = [
    {"pattern": r"\baere[oa]\b", "label": "excl_aereo"},
    {"pattern": r"\bavion\b", "label": "excl_avion"},
    {"pattern": r"\bmaritim[oa]\b", "label": "excl_maritimo"},
    {"pattern": r"\blancha\b", "label": "excl_lancha"},
    {"pattern": r"\bbarcaza\b", "label": "excl_barcaza"},
    {"pattern": r"\bembarcaci[oó]n\b", "label": "excl_embarcacion"},
    {"pattern": r"\bambulancia\b", "label": "excl_ambulancia"},
    {"pattern": r"\blogistic[ao]\b", "label": "excl_logistica"},
    {"pattern": r"\bdistribuci[oó]n\b", "label": "excl_distribucion"},
    {"pattern": r"\bmateriales?\b", "label": "excl_materiales"},
    {"pattern": r"\binsumos?\b", "label": "excl_insumos"},
    {"pattern": r"\bmaquinaria(?:s)?\b", "label": "excl_maquinaria"},
    {"pattern": r"\bequipos?\b", "label": "excl_equipos"},
    {"pattern": r"\bse[ñn]al satelital\b", "label": "excl_senal_satelital"},
    {"pattern": r"\btransporte de vehicul(?:o|os)\b", "label": "excl_transporte_vehiculos"},
    {"pattern": r"\btraslado de vehicul(?:o|os)\b", "label": "excl_traslado_vehiculos"},
    {"pattern": r"\bpatrullaje\b", "label": "excl_patrullaje"},
    {"pattern": r"\bseguridad p[uú]blica\b", "label": "excl_seguridad_publica"},
    {"pattern": r"\bagua potable\b", "label": "excl_agua_potable"},
    {"pattern": r"\bmedicamentos?\b", "label": "excl_medicamentos"},
    {"pattern": r"\breas\b", "label": "excl_reas"},
]


def normalize_text(value):
    if not isinstance(value, str):
        return ""

    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_latest_file(directory, pattern):
    files = sorted(Path(directory).glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No se encontraron archivos {pattern} en {directory}")
    return files[-1]


def load_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def score_text(text):
    positive_hits = []
    negative_hits = []
    score = 0

    for rule in POSITIVE_RULES:
        if re.search(rule["pattern"], text):
            score += rule["score"]
            positive_hits.append(rule["label"])

    for rule in NEGATIVE_RULES:
        if re.search(rule["pattern"], text):
            score += rule["score"]
            negative_hits.append(rule["label"])

    return score, positive_hits, negative_hits


def collect_rule_hits(text, rules):
    hits = []
    for rule in rules:
        if re.search(rule["pattern"], text):
            hits.append(rule["label"])
    return sorted(set(hits))


def classify_transport_row(row, min_score=3):
    nombre = normalize_text(row.get("nombre_licitacion"))
    descripcion = normalize_text(row.get("descripcion"))
    combined = " ".join(part for part in [nombre, descripcion] if part).strip()

    title_score, title_pos, title_neg = score_text(nombre)
    body_score, body_pos, body_neg = score_text(descripcion)
    combined_score, combined_pos, combined_neg = score_text(combined)
    passenger_context_hits = collect_rule_hits(combined, PASSENGER_CONTEXT_RULES)
    land_mode_hits = collect_rule_hits(combined, LAND_MODE_RULES)
    activity_context_hits = collect_rule_hits(combined, ACTIVITY_CONTEXT_RULES)
    domain_context_hits = collect_rule_hits(combined, DOMAIN_CONTEXT_RULES)
    exclusion_hits = collect_rule_hits(combined, EXCLUSION_RULES)

    score = combined_score
    positive_hits = sorted(set(title_pos + body_pos + combined_pos))
    negative_hits = sorted(set(title_neg + body_neg + combined_neg))

    has_strong_phrase = any(
        label in positive_hits
        for label in [
            "transporte_pasajeros",
            "traslado_pasajeros",
            "movilizacion_pasajeros",
            "transporte_escolar",
        ]
    )
    has_generic_transport = "servicio_transporte" in positive_hits
    has_passenger_context = bool(passenger_context_hits)
    has_land_mode = bool(land_mode_hits)
    has_strong_land_mode = any(label in STRONG_LAND_MODE_LABELS for label in land_mode_hits)
    has_activity_context = bool(activity_context_hits)
    has_domain_context = bool(domain_context_hits)
    has_exclusion = bool(exclusion_hits)

    match_fields = []
    if title_score > 0:
        match_fields.append("nombre_licitacion")
    if body_score > 0:
        match_fields.append("descripcion")

    decision_reason = "rejected"
    review_flag = ""

    is_transport = False
    if has_strong_phrase:
        is_transport = True
        decision_reason = "strong_phrase"
    elif score >= min_score and has_generic_transport and (
        has_passenger_context or has_strong_land_mode or has_activity_context or has_domain_context
    ):
        is_transport = True
        decision_reason = "generic_transport_with_context"
    elif score >= min_score and positive_hits and has_strong_land_mode:
        is_transport = True
        decision_reason = "strong_land_mode"
    elif score >= min_score and positive_hits and has_passenger_context and has_land_mode:
        is_transport = True
        decision_reason = "scored_passenger_land_match"
    elif score >= (min_score + 1) and positive_hits and has_passenger_context:
        is_transport = True
        decision_reason = "scored_passenger_context"

    if has_exclusion and not has_strong_phrase:
        is_transport = False
        decision_reason = "rejected_exclusion_context"
    if negative_hits and score <= 0:
        is_transport = False
        decision_reason = "rejected_negative_score"
    if (
        negative_hits
        and any(label in negative_hits for label in ["pasajeros_y_carga", "carga_y_pasajeros"])
    ):
        is_transport = False
        decision_reason = "rejected_mixed_passenger_cargo"
    elif negative_hits and "carga" in negative_hits and not has_strong_phrase and score <= min_score + 1:
        is_transport = False
        decision_reason = "rejected_mixed_cargo"
    if is_transport and score == min_score and has_generic_transport and not (has_passenger_context or has_land_mode):
        review_flag = "borderline_generic"
    if is_transport and has_exclusion and has_strong_phrase:
        review_flag = "mixed_mode_review"

    return {
        "es_transporte": bool(is_transport),
        "transport_score": score,
        "transport_positive_hits": ",".join(positive_hits),
        "transport_negative_hits": ",".join(negative_hits),
        "transport_passenger_context_hits": ",".join(passenger_context_hits),
        "transport_land_mode_hits": ",".join(land_mode_hits),
        "transport_activity_context_hits": ",".join(activity_context_hits),
        "transport_domain_context_hits": ",".join(domain_context_hits),
        "transport_exclusion_hits": ",".join(exclusion_hits),
        "transport_match_fields": ",".join(match_fields),
        "transport_rule": decision_reason,
        "transport_review_flag": review_flag,
    }


def classify_dataframe(df, min_score=3):
    if "nombre_licitacion" not in df.columns:
        raise ValueError("El dataset no tiene la columna nombre_licitacion")

    classified = df.apply(
        lambda row: classify_transport_row(row, min_score=min_score),
        axis=1,
        result_type="expand",
    )

    return pd.concat([df.copy(), classified], axis=1)


def filter_transport_dataframe(df, min_score=3):
    classified = classify_dataframe(df, min_score=min_score)
    filtered = classified[classified["es_transporte"]].copy()
    return classified, filtered


def filter_processed_files(processed_files, min_score=3):
    filtered_frames = []
    summary_rows = []
    rule_counter = {}
    review_counter = {}

    for processed_path in processed_files:
        df = load_csv(processed_path)
        classified, filtered = filter_transport_dataframe(df, min_score=min_score)

        if not filtered.empty:
            filtered["transport_source_file"] = processed_path.name
            filtered_frames.append(filtered)

            for rule, count in filtered["transport_rule"].fillna("").value_counts().items():
                rule_counter[rule] = rule_counter.get(rule, 0) + int(count)
            for flag, count in filtered["transport_review_flag"].fillna("").value_counts().items():
                if not flag:
                    continue
                review_counter[flag] = review_counter.get(flag, 0) + int(count)

        summary_rows.append({
            "processed_file": str(processed_path),
            "input_rows": int(len(df)),
            "transport_rows": int(len(filtered)),
            "candidate_rules": (
                classified[classified["es_transporte"]]["transport_rule"]
                .fillna("")
                .value_counts()
                .to_dict()
            ),
        })

    if filtered_frames:
        result_df = pd.concat(filtered_frames, ignore_index=True)
        result_df = result_df.drop_duplicates(subset=["codigo_licitacion"], keep="last")
    else:
        result_df = pd.DataFrame()

    return result_df, summary_rows, rule_counter, review_counter


def write_transport_selection(
    df_filtered,
    summary_rows,
    source_label,
    rule_counter=None,
    review_counter=None,
    output_dir=TRANSPORT_DIR,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filtered_path = output_dir / f"licitaciones_transport_candidates_{source_label}_{timestamp}.csv"
    summary_path = output_dir / f"licitaciones_transport_candidates_summary_{source_label}_{timestamp}.json"

    df_filtered.to_csv(filtered_path, index=False, encoding="utf-8-sig")

    summary = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_label": source_label,
            "output_dir": str(output_dir),
        },
        "results": {
            "source_files": len(summary_rows),
            "transport_rows": int(len(df_filtered)),
            "rule_counts": rule_counter or {},
            "review_flag_counts": review_counter or {},
        },
        "files": summary_rows,
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return {
        "filtered_path": filtered_path,
        "summary_path": summary_path,
        "transport_rows": len(df_filtered),
        "source_files": len(summary_rows),
    }


def run_transport_selection(processed_files, min_score=3, source_label="batch"):
    filtered_df, summary_rows, rule_counter, review_counter = filter_processed_files(
        processed_files,
        min_score=min_score,
    )
    outputs = write_transport_selection(
        filtered_df,
        summary_rows,
        source_label=source_label,
        rule_counter=rule_counter,
        review_counter=review_counter,
    )

    print(f"[INFO] Archivos processed analizados: {outputs['source_files']}")
    print(f"[INFO] Filas transporte detectadas: {outputs['transport_rows']}")
    print(f"[OK] Archivo candidatos transporte: {outputs['filtered_path']}")
    print(f"[INFO] Resumen candidatos: {outputs['summary_path']}")

    return outputs


def run_transport_filter(input_path=None, min_score=3):
    if input_path is None:
        input_path = find_latest_file(PROCESSED_DIR, "licitaciones_processed_*.csv")

    df = load_csv(input_path)
    classified_df, filtered_df = filter_transport_dataframe(df, min_score=min_score)

    TRANSPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filtered_path = TRANSPORT_DIR / f"licitaciones_transport_{timestamp}.csv"
    review_path = TRANSPORT_DIR / f"licitaciones_transport_review_{timestamp}.csv"

    filtered_df.to_csv(filtered_path, index=False, encoding="utf-8-sig")
    classified_df.to_csv(review_path, index=False, encoding="utf-8-sig")

    return {
        "filtered_path": filtered_path,
        "review_path": review_path,
        "total_input_rows": len(classified_df),
        "total_transport_rows": len(filtered_df),
    }


def main():
    parser = argparse.ArgumentParser(description="Clasifica licitaciones de transporte.")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=None,
        help="CSV processed especifico. Si no se entrega, usa el ultimo processed.",
    )
    parser.add_argument(
        "--min-score",
        type=int,
        default=3,
        help="Puntaje minimo para clasificar como transporte.",
    )
    args = parser.parse_args()

    outputs = run_transport_filter(input_path=args.input_file, min_score=args.min_score)
    print(f"[INFO] Total licitaciones: {outputs['total_input_rows']}")
    print(f"[INFO] Total transporte: {outputs['total_transport_rows']}")
    print(f"[OK] Archivo transporte: {outputs['filtered_path']}")
    print(f"[INFO] Archivo revision: {outputs['review_path']}")


if __name__ == "__main__":
    main()
