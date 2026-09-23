"""Explicit Asia/Almaty wall-clock representation shared by history and weather.

Naive source values mean Asia/Almaty, never UTC or the machine timezone.
Named-zone Asia/Almaty inputs keep their clock hour when the zone is removed
for the existing hourly CSV format. Other aware zones are rejected, not converted.
This preserves the historical dataset's wall-clock grid, including the ambiguous
local hour at Kazakhstan's 2024 offset change; no UTC instant is invented for it.
"""
import pandas as pd
from src.config import TIMEZONE


def local_timestamps(values: pd.Series, *, errors="raise") -> pd.Series:
    parsed = pd.to_datetime(values, errors=errors)
    try:
        zone = parsed.dt.tz
    except AttributeError as exc:
        raise ValueError(f"Use uniform {TIMEZONE} timestamps, not mixed offsets") from exc
    if zone is not None:
        if str(zone) != TIMEZONE:
            raise ValueError(f"Expected {TIMEZONE}, got {zone}; no automatic timezone conversion")
        parsed = parsed.dt.tz_localize(None)  # Preserve local clock, not UTC conversion.
    return parsed


def local_timestamp(value) -> pd.Timestamp:
    return local_timestamps(pd.Series([value])).iloc[0]


def local_history(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in ("timestamp", "available_at", "forecast_origin"):
        if column in result:
            result[column] = local_timestamps(result[column])
    return result
