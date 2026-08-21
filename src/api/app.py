from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query

from .repositories import DataRepository
from .services import LicitacionesService, MarketService, MetadataService, SystemService


app = FastAPI(
    title="TransData API",
    description="Backend MVP para la aplicacion web de TransData.",
    version="0.1.0",
)


def get_repository() -> DataRepository:
    return DataRepository()


def get_licitaciones_service(repository: DataRepository = Depends(get_repository)) -> LicitacionesService:
    return LicitacionesService(repository)


def get_metadata_service(repository: DataRepository = Depends(get_repository)) -> MetadataService:
    return MetadataService(repository)


def get_market_service(repository: DataRepository = Depends(get_repository)) -> MarketService:
    return MarketService(repository)


def get_system_service(repository: DataRepository = Depends(get_repository)) -> SystemService:
    return SystemService(repository)


@app.get("/api/licitaciones")
def list_licitaciones(
    service: LicitacionesService = Depends(get_licitaciones_service),
    q: str | None = None,
    estado_bucket: Annotated[list[str] | None, Query()] = None,
    region: Annotated[list[str] | None, Query()] = None,
    comuna: Annotated[list[str] | None, Query()] = None,
    periodo_publicacion: Annotated[list[str] | None, Query()] = None,
    revision_segmento: Annotated[list[str] | None, Query()] = None,
    revision_prioridad: Annotated[list[str] | None, Query()] = None,
    revision_decision: Annotated[list[str] | None, Query()] = None,
    adjudicacion_capturada: str | None = None,
    requiere_refresh_adjudicacion: str | None = None,
    page: int = 1,
    page_size: int = 25,
    sort: str = "fecha_publicacion:desc",
):
    return service.list_licitaciones(
        q=q,
        estado_bucket=estado_bucket,
        region=region,
        comuna=comuna,
        periodo_publicacion=periodo_publicacion,
        revision_segmento=revision_segmento,
        revision_prioridad=revision_prioridad,
        revision_decision=revision_decision,
        adjudicacion_capturada=adjudicacion_capturada,
        requiere_refresh_adjudicacion=requiere_refresh_adjudicacion,
        page=page,
        page_size=page_size,
        sort=sort,
    )


@app.get("/api/licitaciones/{codigo_licitacion}")
def get_licitacion_detail(codigo_licitacion: str, service: LicitacionesService = Depends(get_licitaciones_service)):
    record = service.get_licitacion_detail(codigo_licitacion)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "not_found",
                    "message": "No existe licitacion para el codigo solicitado.",
                    "details": {"codigo_licitacion": codigo_licitacion},
                }
            },
        )
    return {"data": record}


@app.get("/api/metadata/filters")
def get_filters(service: MetadataService = Depends(get_metadata_service)):
    return service.filters()


@app.get("/api/metadata/contract")
def get_contract(service: MetadataService = Depends(get_metadata_service)):
    return service.contract()


@app.get("/api/market/summary")
def get_market_summary(service: MarketService = Depends(get_market_service)):
    return service.summary()


@app.get("/api/market/buyers")
def get_market_buyers(
    service: MarketService = Depends(get_market_service),
    page: int = 1,
    page_size: int = 25,
    region: Annotated[list[str] | None, Query()] = None,
    sort: str = "licitaciones:desc",
):
    return service.buyers(page=page, page_size=page_size, region=region, sort=sort)


@app.get("/api/market/regions")
def get_market_regions(
    service: MarketService = Depends(get_market_service),
    region: Annotated[list[str] | None, Query()] = None,
    periodo_publicacion: Annotated[list[str] | None, Query()] = None,
    estado_bucket: Annotated[list[str] | None, Query()] = None,
):
    return service.regions(region=region, periodo_publicacion=periodo_publicacion, estado_bucket=estado_bucket)


@app.get("/api/system/health")
def get_system_health(service: SystemService = Depends(get_system_service)):
    return service.health()


@app.get("/api/system/quality")
def get_system_quality(service: SystemService = Depends(get_system_service)):
    return service.quality()


@app.get("/api/ping")
def ping():
    return {"ok": True}
