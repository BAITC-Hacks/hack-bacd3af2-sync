from datetime import UTC, date, datetime, time, timedelta

import pandas as pd


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def forecast_origin_for(forecast_date: date) -> datetime:
    """The moment the forecast is issued: midnight (local wall-clock) of the forecast date."""
    return datetime.combine(forecast_date, time.min)


def hourly_range(start: datetime, hours: int) -> pd.DatetimeIndex:
    """`hours` hourly timestamps starting at `start` (inclusive)."""
    return pd.date_range(start=start, periods=hours, freq="h")


def horizon_end(start: datetime, hours: int) -> datetime:
    """Last timestamp covered by a forecast of `hours` hourly points."""
    return start + timedelta(hours=hours - 1)
