"""Load raw CSV values without deleting, imputing, or clipping observations."""
from pathlib import Path
import pandas as pd
from src.time_utils import local_timestamps

COLUMNS = {
    "ID": "id",
    "Статистическое время": "timestamp",
    "Средняя скорость ветра(m/s)": "wind_speed",
    "Нормализованная активная мощность": "power",
    "Средняя температура окружающей среды(°C)": "temperature",
}
NUMERIC_COLUMNS = ("wind_speed", "power", "temperature")


def load_raw(path: str | Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype="string", keep_default_na=False)
    raw.columns = raw.columns.str.strip()
    if raw.columns.duplicated().any():
        raise ValueError("Duplicate column names after whitespace normalization")
    missing = set(COLUMNS) - set(raw.columns)
    extra = set(raw.columns) - set(COLUMNS)
    if missing or extra:
        raise ValueError(f"Unexpected CSV schema: missing={sorted(missing)}, extra={sorted(extra)}")
    return raw.rename(columns=COLUMNS)


def parse_raw(raw: pd.DataFrame) -> pd.DataFrame:
    parsed = raw.copy()
    parsed["timestamp"] = pd.to_datetime(
        raw["timestamp"].str.strip(), format="%Y-%m-%d %H:%M:%S", errors="coerce"
    )
    parsed["timestamp"] = local_timestamps(parsed["timestamp"], errors="coerce")
    for column in NUMERIC_COLUMNS:
        parsed[column] = pd.to_numeric(raw[column], errors="coerce").astype(float)
    return parsed
