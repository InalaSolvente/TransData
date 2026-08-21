from __future__ import annotations

from src.api.repositories import DataRepository
from src.api.services import LicitacionesService, MarketService, MetadataService, SystemService


def test_licitaciones_listing():
    service = LicitacionesService(DataRepository())
    payload = service.list_licitaciones(page=1, page_size=2)
    assert "data" in payload
    assert "pagination" in payload
    assert len(payload["data"]) <= 2


def test_licitacion_detail_from_listing():
    service = LicitacionesService(DataRepository())
    payload = service.list_licitaciones(page=1, page_size=1)
    assert payload["data"]
    codigo = payload["data"][0]["codigo_licitacion"]
    detail = service.get_licitacion_detail(codigo)
    assert detail is not None
    assert detail["codigo_licitacion"] == codigo


def test_metadata_filters():
    service = MetadataService(DataRepository())
    payload = service.filters()
    assert "data" in payload
    assert "estado_bucket" in payload["data"]


def test_market_summary():
    service = MarketService(DataRepository())
    payload = service.summary()
    assert "data" in payload
    assert "rows" in payload["data"]


def test_system_quality():
    service = SystemService(DataRepository())
    payload = service.quality()
    assert "summary" in payload
    assert "issues" in payload
