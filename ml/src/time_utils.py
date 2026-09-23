"""Explicit Asia/Almaty wall-clock representation shared by history and weather.

Naive source values mean Asia/Almaty, never UTC or the machine timezone.
Named-zone Asia/Almaty inputs keep their clock hour when the zone is removed
for the existing hourly CSV format. Serialized fixed offsets are accepted only
when they match Asia/Almaty on that date. Other zones are rejected, not converted.
This preserves the historical dataset's wall-clock grid, including the ambiguous
local hour at Kazakhstan's 2024 offset change; no UTC instant is invented for it.
"""
import pandas as pd
from datetime import timezone, timedelta
from zoneinfo import ZoneInfo
from src.config import TIMEZONE


def local_timestamps(values: pd.Series, *, errors="raise") -> pd.Series:
    parsed = pd.to_datetime(values, errors=errors)
    try:
        zone = parsed.dt.tz
    except AttributeError as exc:
        raise ValueError(f"Use uniform {TIMEZONE} timestamps, not mixed offsets") from exc
    if zone is not None:
        if str(zone) != TIMEZONE:
            # CSV serialization loses the IANA name. Accept only fixed offsets
            # matching Asia/Almaty on each date, preserving the same wall clock.
            if not isinstance(zone, timezone) or zone.utcoffset(None) == timedelta(0):
                raise ValueError(f"Expected {TIMEZONE}, got {zone}; no automatic timezone conversion")
            for value in parsed.dropna():
                clock = value.to_pydatetime().replace(tzinfo=None)
                offsets = {clock.replace(tzinfo=ZoneInfo(TIMEZONE), fold=fold).utcoffset() for fold in (0, 1)}
                if value.utcoffset() not in offsets:
                    raise ValueError(f"Offset does not match {TIMEZONE} at {clock}")
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
