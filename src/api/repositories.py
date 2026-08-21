from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ANALYTICS_DIR, CONTRACT_PATH, DETAIL_PATH, LISTING_PATH, MANIFEST_PATH, QUALITY_DIR, REPORTS_DIR
from .utils import latest_file


class DataRepository:
    def __init__(
        self,
        listing_path: Path = LISTING_PATH,
        detail_path: Path = DETAIL_PATH,
        manifest_path: Path = MANIFEST_PATH,
        contract_path: Path = CONTRACT_PATH,
        analytics_dir: Path = ANALYTICS_DIR,
        reports_dir: Path = REPORTS_DIR,
        quality_dir: Path = QUALITY_DIR,
    ) -> None:
        self.listing_path = listing_path
        self.detail_path = detail_path
        self.manifest_path = manifest_path
        self.contract_path = contract_path
        self.analytics_dir = analytics_dir
        self.reports_dir = reports_dir
        self.quality_dir = quality_dir

    def listing_df(self) -> pd.DataFrame:
        return pd.read_csv(self.listing_path, encoding="utf-8-sig", parse_dates=["fecha_publicacion", "fecha_cierre"], keep_default_na=True)

    def detail_df(self) -> pd.DataFrame:
        return pd.read_csv(self.detail_path, encoding="utf-8-sig", parse_dates=["fecha_publicacion", "fecha_cierre"], keep_default_na=True)

    def manifest(self) -> dict[str, Any]:
        with self.manifest_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def contract(self) -> dict[str, Any]:
        with self.contract_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def market_summary(self) -> dict[str, Any]:
        path = latest_file(self.analytics_dir, "transport_analytics_summary_*.json")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def buyers_df(self) -> pd.DataFrame:
        path = latest_file(self.analytics_dir, "transport_agg_buyers_*.csv")
        return pd.read_csv(path, encoding="utf-8-sig")

    def regions_df(self) -> pd.DataFrame:
        path = latest_file(self.analytics_dir, "transport_agg_region_period_*.csv")
        return pd.read_csv(path, encoding="utf-8-sig")

    def health(self) -> dict[str, Any]:
        path = latest_file(self.reports_dir, "mp_pipeline_health_*.json")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def quality_summary(self) -> dict[str, Any]:
        path = latest_file(self.quality_dir, "transport_quality_summary_*.json")
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def quality_issues_df(self) -> pd.DataFrame:
        path = latest_file(self.quality_dir, "transport_quality_issues_*.csv")
        return pd.read_csv(path, encoding="utf-8-sig")
