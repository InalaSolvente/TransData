from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "transform"))

from apply_transport_manual_review import apply_manual_review_to_dataframe  # noqa: E402


def make_row(codigo, nombre, descripcion="", es_transporte=True, review_flag="", domain_hits="", activity_hits=""):
    return {
        "codigo_licitacion": codigo,
        "nombre_licitacion": nombre,
        "descripcion": descripcion,
        "es_transporte": es_transporte,
        "transport_review_flag": review_flag,
        "transport_domain_context_hits": domain_hits,
        "transport_activity_context_hits": activity_hits,
        "transport_positive_hits": "servicio_transporte" if es_transporte else "",
        "transport_exclusion_hits": "",
    }


def apply_single(row, manual_rows=None):
    df = pd.DataFrame([row])
    manual_df = pd.DataFrame(manual_rows or [])
    result_df, _ = apply_manual_review_to_dataframe(df, manual_df)
    return result_df.iloc[0]


@pytest.mark.parametrize("codigo", ["1049-58-CO25", "1049-59-CO25", "1049-40-LE25", "1049-41-LE25"])
def test_lancha_bio_oceanografico_is_excluded(codigo):
    row = make_row(
        codigo,
        "SERVICIO DE TRASLADO DE PASAJEROS EN LANCHA MENOR",
        "Muestreo bio-oceanografico mensual en la localidad de Coliumo.",
        es_transporte=True,
        review_flag="mixed_mode_review",
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "EXCLUIR"
    assert bool(result["revision_incluir_master_core"]) is False
    assert bool(result["flag_non_land_mode"]) is True


@pytest.mark.parametrize("codigo", ["5061-162-L122", "5061-92-L122"])
def test_medicamentos_domicilio_is_excluded_as_logistics(codigo):
    row = make_row(
        codigo,
        "Servicio de transporte para entrega de medicamentos a domicilio",
        "Farmacia municipal con entrega de medicamentos a domicilio.",
        es_transporte=True,
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "EXCLUIR"
    assert bool(result["revision_incluir_master_core"]) is False
    assert bool(result["flag_logistics_not_passenger"]) is True


def test_asset_purchase_ambulancia_is_excluded():
    row = make_row(
        "2790-144-LQ22",
        "Adquisicion de ambulancia y vehiculo",
        "Compra de ambulancia y vehiculo para la unidad de salud.",
        es_transporte=True,
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "EXCLUIR"
    assert bool(result["revision_incluir_master_core"]) is False
    assert bool(result["flag_asset_purchase"]) is True


@pytest.mark.parametrize("codigo", ["1195104-26-LR24", "1195104-3-LR24"])
def test_sermig_codes_stay_manual_review(codigo):
    row = make_row(
        codigo,
        "Servicio de traslado de pasajeros SERMIG",
        "Componente terrestre, maritimo y aereo para traslado de pasajeros.",
        es_transporte=True,
        review_flag="mixed_mode_review",
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "REVISAR_MANUAL"
    assert bool(result["revision_incluir_master_core"]) is False
    assert bool(result["flag_multimodal_review"]) is True


def test_education_transport_is_included():
    row = make_row(
        "4364-6-LE26",
        "SERVICIO DE TRANSPORTE ESCUELA PASO EL ROBLE",
        "Servicio de transporte para estudiantes de escuela rural.",
        es_transporte=True,
        domain_hits="dom_escuela",
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "INCLUIR"
    assert bool(result["revision_incluir_master_core"]) is True
    assert bool(result["flag_education_transport"]) is True


def test_health_transport_is_included():
    row = make_row(
        "1214102-27-LP26",
        "SERVICIO DE TRANSPORTE PARA CENTROS DE SALUD",
        "Servicio de transporte para atencion primaria de salud.",
        es_transporte=True,
        domain_hits="dom_aps,dom_centros_salud",
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "INCLUIR"
    assert bool(result["revision_incluir_master_core"]) is True
    assert bool(result["flag_health_transport"]) is True


def test_mixed_bundle_is_partial_include():
    row = make_row(
        "3736-123-L124",
        "Servicio de Transporte, Pago de Entradas y Alimentacion para Viaje Pedagogico",
        "Incluye transporte, pago de entradas y alimentacion para viaje pedagogico.",
        es_transporte=True,
        activity_hits="ctx_salidas_pedagogicas",
    )
    result = apply_single(row)
    assert result["revision_decision_transdata"] == "INCLUIR_PARCIAL"
    assert bool(result["revision_incluir_master_core"]) is True
    assert bool(result["flag_mixed_bundle"]) is True
    assert bool(result["flag_clean_transport_amount"]) is False


def test_manual_review_override_is_applied_by_codigo():
    row = make_row(
        "9999-1-LE26",
        "SERVICIO DE TRANSPORTE GENERICO",
        "Servicio generico.",
        es_transporte=True,
    )
    manual_rows = [
        {
            "codigo_licitacion": "9999-1-LE26",
            "revision_decision_transdata": "INCLUIR_PARCIAL",
            "revision_incluir_master_core": True,
            "revision_prioridad_negocio": "MEDIA",
            "revision_confianza": "ALTA",
            "revision_segmento_validado": "educacion",
            "revision_motivo": "override manual",
            "revision_importancia": "alta",
            "revision_accion_recomendada": "mantener",
        }
    ]
    result = apply_single(row, manual_rows=manual_rows)
    assert result["revision_decision_transdata"] == "INCLUIR_PARCIAL"
    assert bool(result["revision_incluir_master_core"]) is True
    assert result["revision_prioridad_negocio"] == "MEDIA"
    assert result["revision_decision_source"] == "manual_review"
