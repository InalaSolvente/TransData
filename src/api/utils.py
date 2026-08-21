from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def latest_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)
    if not matches:
        raise FileNotFoundError(f"No se encontraron archivos para {pattern} en {directory}")
    return matches[0]


def normalize_multi_value(raw: list[str] | str | None) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        raw_values = [raw]
    else:
        raw_values = raw

    values: list[str] = []
    for item in raw_values:
        if item is None:
            continue
        for piece in str(item).split(","):
            cleaned = piece.strip()
            if cleaned:
                values.append(cleaned)
    return values


def normalize_bool_param(raw: str | None) -> bool | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"true", "1", "si", "yes"}:
        return True
    if value in {"false", "0", "no"}:
        return False
    return None


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def serialize_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: json_safe(value) for key, value in record.items()}
