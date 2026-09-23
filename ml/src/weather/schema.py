import numbers
import numpy as np
import pandas as pd
from src.config import WEATHER_COLUMNS
from src.time_utils import local_timestamp, local_timestamps


def validate_weather(turbine_id, weather, horizon_hours, forecast_origin):
    """Return a sorted copy in the explicit Asia/Almaty wall-clock convention."""
    if isinstance(turbine_id, bool) or not isinstance(turbine_id, numbers.Integral) or turbine_id not in (1, 2):
        raise ValueError("turbine_id must be integer 1 or 2")
    if isinstance(horizon_hours, bool) or not isinstance(horizon_hours, numbers.Integral) or horizon_hours not in (24, 48):
        raise ValueError("horizon_hours must be integer 24 or 48")
    origin = local_timestamp(forecast_origin)
    if pd.isna(origin) or origin != origin.floor("h"):
        raise ValueError("forecast_origin must be a valid whole hour in Asia/Almaty")
    if not isinstance(weather, pd.DataFrame):
        raise ValueError("weather must be a pandas DataFrame")
    if weather.columns.duplicated().any():
        raise ValueError("Duplicate weather column names")
    if set(WEATHER_COLUMNS) - set(weather):
        raise ValueError(f"Missing weather columns: {sorted(set(WEATHER_COLUMNS) - set(weather))}")
    if len(weather) != horizon_hours:
        raise ValueError(f"Expected exactly {horizon_hours} weather rows")
    frame = weather.loc[:, list(WEATHER_COLUMNS)].copy()
    for column in ("timestamp", "forecast_origin"):
        frame[column] = local_timestamps(frame[column])
        if frame[column].isna().any():
            raise ValueError(f"Missing {column}")
    if not frame.forecast_origin.eq(origin).all():
        raise ValueError("Every weather forecast_origin must match the requested origin")
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    expected = pd.date_range(origin, periods=horizon_hours, freq="h")
    if not pd.DatetimeIndex(frame.timestamp).equals(expected):
        raise ValueError("Weather must cover each requested hour exactly once, starting at forecast_origin")
    for column in ("wind_speed", "temperature", "latitude", "longitude"):
        if frame[column].map(lambda value: isinstance(value, (bool, np.bool_))).any():
            raise ValueError(f"Boolean values are not valid {column}")
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype(float)
        if not np.isfinite(frame[column]).all():
            raise ValueError(f"Weather {column} must contain finite values")
    if frame.wind_speed.lt(0).any():
        raise ValueError("Wind speed cannot be negative")
    if frame.temperature.lt(-273.15).any():
        raise ValueError("Temperature cannot be below absolute zero")
    if not frame.latitude.between(-90, 90).all() or not frame.longitude.between(-180, 180).all():
        raise ValueError("Invalid geographic coordinates")
    if frame.latitude.nunique() != 1 or frame.longitude.nunique() != 1:
        raise ValueError("A turbine weather batch must describe one location")
    return frame, origin
