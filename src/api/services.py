from __future__ import annotations

from math import ceil
from typing import Any

import pandas as pd

from .repositories import DataRepository
from .utils import json_safe, normalize_bool_param, normalize_multi_value, serialize_record


LISTING_SORTABLE_FIELDS = {
    "fecha_publicacion",
    "fecha_cierre",
    "monto_estimado",
    "monto_adjudicado",
    "transport_score",
    "nombre",
    "comprador_nombre",
}


class LicitacionesService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def list_licitaciones(
        self,
        *,
        q: str | None = None,
        estado_bucket: list[str] | str | None = None,
        region: list[str] | str | None = None,
        comuna: list[str] | str | None = None,
        periodo_publicacion: list[str] | str | None = None,
        revision_segmento: list[str] | str | None = None,
        revision_prioridad: list[str] | str | None = None,
        revision_decision: list[str] | str | None = None,
        adjudicacion_capturada: str | None = None,
        requiere_refresh_adjudicacion: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort: str = "fecha_publicacion:desc",
    ) -> dict[str, Any]:
        df = self.repository.listing_df().copy()
        df = self._apply_filters(
            df,
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
        )

        sort_field, sort_direction = self._parse_sort(sort)
        ascending = sort_direction == "asc"
        df = df.sort_values(by=[sort_field, "codigo_licitacion"], ascending=[ascending, True], na_position="last")

        total_results = len(df)
        page_size = max(1, min(page_size, 100))
        total_pages = max(1, ceil(total_results / page_size)) if total_results else 1
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        data = [serialize_record(record) for record in page_df.to_dict(orient="records")]
        applied_filters = {
            "estado_bucket": normalize_multi_value(estado_bucket),
            "region": normalize_multi_value(region),
            "comuna": normalize_multi_value(comuna),
            "periodo_publicacion": normalize_multi_value(periodo_publicacion),
            "revision_segmento": normalize_multi_value(revision_segmento),
            "revision_prioridad": normalize_multi_value(revision_prioridad),
            "revision_decision": normalize_multi_value(revision_decision),
            "adjudicacion_capturada": normalize_bool_param(adjudicacion_capturada),
            "requiere_refresh_adjudicacion": normalize_bool_param(requiere_refresh_adjudicacion),
            "q": q or "",
        }

        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total_results,
                "total_pages": total_pages,
            },
            "applied_filters": applied_filters,
            "sort": {"field": sort_field, "direction": sort_direction},
        }

    def get_licitacion_detail(self, codigo_licitacion: str) -> dict[str, Any] | None:
        df = self.repository.detail_df()
        match = df[df["codigo_licitacion"].astype(str) == str(codigo_licitacion)]
        if match.empty:
            return None
        record = match.iloc[0].to_dict()
        return serialize_record(record)

    def _apply_filters(self, df: pd.DataFrame, **filters: Any) -> pd.DataFrame:
        result = df
        q = filters.get("q")
        if q:
            query = str(q).strip().lower()
            text = (
                result["codigo_licitacion"].fillna("").astype(str).str.lower()
                + " "
                + result["nombre"].fillna("").astype(str).str.lower()
                + " "
                + result["comprador_nombre"].fillna("").astype(str).str.lower()
            )
            result = result[text.str.contains(query, na=False)]

        for field in ["estado_bucket", "region", "comuna", "periodo_publicacion", "revision_segmento", "revision_prioridad", "revision_decision"]:
            values = normalize_multi_value(filters.get(field))
            if values:
                normalized = {value.strip().lower() for value in values}
                result = result[result[field].fillna("").astype(str).str.lower().isin(normalized)]

        for field in ["adjudicacion_capturada", "requiere_refresh_adjudicacion"]:
            value = normalize_bool_param(filters.get(field))
            if value is not None:
                result = result[result[field].fillna(False).astype(bool) == value]

        return result

    def _parse_sort(self, raw_sort: str) -> tuple[str, str]:
        field = "fecha_publicacion"
        direction = "desc"
        if raw_sort:
            parts = raw_sort.split(":")
            if parts and parts[0] in LISTING_SORTABLE_FIELDS:
                field = parts[0]
            if len(parts) > 1 and parts[1].lower() in {"asc", "desc"}:
                direction = parts[1].lower()
        return field, direction


class MetadataService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def filters(self) -> dict[str, Any]:
        manifest = self.repository.manifest()
        return {"data": manifest.get("filters", {})}

    def contract(self) -> dict[str, Any]:
        return self.repository.contract()


class MarketService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def summary(self) -> dict[str, Any]:
        return {"data": self.repository.market_summary()}

    def buyers(self, *, page: int = 1, page_size: int = 25, region: list[str] | str | None = None, sort: str = "licitaciones:desc") -> dict[str, Any]:
        df = self.repository.buyers_df().copy()
        regions = normalize_multi_value(region)
        if regions:
            normalized = {value.strip().lower() for value in regions}
            df = df[df["comprador_region_final"].fillna("").astype(str).str.lower().isin(normalized)]

        sort_field, sort_direction = self._parse_sort(sort, allowed={"licitaciones", "monto_estimado_total", "monto_adjudicado_total"})
        ascending = sort_direction == "asc"
        df = df.sort_values(by=[sort_field], ascending=[ascending], na_position="last")
        return self._paginate_df(df, page=page, page_size=page_size)

    def regions(self, *, region: list[str] | str | None = None, periodo_publicacion: list[str] | str | None = None, estado_bucket: list[str] | str | None = None) -> dict[str, Any]:
        df = self.repository.regions_df().copy()
        region_values = normalize_multi_value(region)
        period_values = normalize_multi_value(periodo_publicacion)
        status_values = normalize_multi_value(estado_bucket)
        if region_values:
            normalized = {value.strip().lower() for value in region_values}
            df = df[df["comprador_region_final"].fillna("").astype(str).str.lower().isin(normalized)]
        if period_values:
            normalized = {value.strip().lower() for value in period_values}
            df = df[df["publicacion_periodo"].fillna("").astype(str).str.lower().isin(normalized)]
        if status_values:
            normalized = {value.strip().lower() for value in status_values}
            df = df[df["estado_grupo"].fillna("").astype(str).str.lower().isin(normalized)]

        data = [serialize_record(record) for record in df.to_dict(orient="records")]
        return {"data": data}

    def _paginate_df(self, df: pd.DataFrame, *, page: int, page_size: int) -> dict[str, Any]:
        total_results = len(df)
        page_size = max(1, min(page_size, 100))
        total_pages = max(1, ceil(total_results / page_size)) if total_results else 1
        page = max(1, min(page, total_pages))
        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]
        data = [serialize_record(record) for record in page_df.to_dict(orient="records")]
        return {
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total_results,
                "total_pages": total_pages,
            },
        }

    def _parse_sort(self, raw_sort: str, allowed: set[str]) -> tuple[str, str]:
        field = next(iter(allowed))
        direction = "desc"
        if raw_sort:
            parts = raw_sort.split(":")
            if parts and parts[0] in allowed:
                field = parts[0]
            if len(parts) > 1 and parts[1].lower() in {"asc", "desc"}:
                direction = parts[1].lower()
        return field, direction


class SystemService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def health(self) -> dict[str, Any]:
        return self.repository.health()

    def quality(self) -> dict[str, Any]:
        summary = self.repository.quality_summary()
        issues_df = self.repository.quality_issues_df()
        issues = [serialize_record(record) for record in issues_df.to_dict(orient="records")]
        return {"summary": summary, "issues": issues}
