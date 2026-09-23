import numpy as np
import pandas as pd
from src.time_utils import local_timestamps

WEATHER_FEATURES = ["wind_speed", "temperature"]
FEATURES = WEATHER_FEATURES + ["hour", "day_of_week", "month", "day_of_year",
    "hour_sin", "hour_cos", "day_of_year_sin", "day_of_year_cos",
    "wind_speed_squared", "wind_speed_cubed", "wind_temperature"]


def build_features(weather: pd.DataFrame) -> pd.DataFrame:
    """No target, lag, fitting or observed intra-hour statistics are used.

    History and backend weather share Asia/Almaty clock hours. No UTC conversion.
    Backend supplies wind_speed and temperature already mapped from its provider.
    """
    missing = {"timestamp", *WEATHER_FEATURES} - set(weather.columns)
    if missing:
        raise ValueError(f"Missing feature inputs: {sorted(missing)}")
    timestamp = local_timestamps(weather.timestamp)
    if timestamp.isna().any():
        raise ValueError("Expected valid Asia/Almaty timestamps")
    values = weather[WEATHER_FEATURES].astype(float)
    if not np.isfinite(values.to_numpy()).all() or values.wind_speed.lt(0).any():
        raise ValueError("Weather must be finite with nonnegative wind speed")
    result = values.copy()
    result["hour"] = timestamp.dt.hour
    result["day_of_week"] = timestamp.dt.dayofweek
    result["month"] = timestamp.dt.month
    result["day_of_year"] = timestamp.dt.dayofyear
    result["hour_sin"] = np.sin(2 * np.pi * result.hour / 24)
    result["hour_cos"] = np.cos(2 * np.pi * result.hour / 24)
    year_length = np.where(timestamp.dt.is_leap_year, 366, 365)
    result["day_of_year_sin"] = np.sin(2 * np.pi * (result.day_of_year - 1) / year_length)
    result["day_of_year_cos"] = np.cos(2 * np.pi * (result.day_of_year - 1) / year_length)
    result["wind_speed_squared"] = result.wind_speed ** 2
    result["wind_speed_cubed"] = result.wind_speed ** 3
    result["wind_temperature"] = result.wind_speed * result.temperature
    if not np.isfinite(result.to_numpy()).all():
        raise ValueError("Nonfinite derived features")
    return result[FEATURES]
