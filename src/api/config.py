from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SERVING_DIR = DATA_DIR / "serving"
ANALYTICS_DIR = DATA_DIR / "analytics"
REPORTS_DIR = DATA_DIR / "reports"
QUALITY_DIR = REPORTS_DIR / "quality"

LISTING_PATH = SERVING_DIR / "transport_app_listing_latest.csv"
DETAIL_PATH = SERVING_DIR / "transport_app_detail_latest.csv"
MANIFEST_PATH = SERVING_DIR / "transport_dataset_manifest_latest.json"
CONTRACT_PATH = SERVING_DIR / "transport_app_contract_latest.json"
