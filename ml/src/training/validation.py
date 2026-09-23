"""Strict boundaries for observed-weather proxy experiments, not weather backtests."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import TRAINING_CUTOFF
from src.time_utils import local_history, local_timestamp


def validate_history(frame: pd.DataFrame) -> None:
    frame = local_history(frame)
    required = {"timestamp", "available_at", "power_mean", "wind_speed_mean", "temperature_mean",
                "training_eligible", "observation_count", "wind_speed_count", "temperature_count", "power_count"}
    if required - set(frame):
        raise ValueError(f"Missing hourly columns: {sorted(required - set(frame))}")
    if frame.empty or frame.timestamp.isna().any() or frame.available_at.isna().any():
        raise ValueError("History must have valid timestamps and availability times")
    cutoff = pd.Timestamp(TRAINING_CUTOFF)
    # Fail rather than silently filtering accidentally supplied February data.
    if frame.timestamp.ge(cutoff).any() or frame.available_at.gt(cutoff).any():
        raise ValueError("Leakage guard: February 2026 or later data is forbidden in training input")
    if frame.timestamp.duplicated().any() or not frame.timestamp.is_monotonic_increasing:
        raise ValueError("History must have sorted, unique timestamps")
    if not frame.timestamp.eq(frame.timestamp.dt.floor("h")).all():
        raise ValueError("Timestamps must label whole hours")
    if not frame.available_at.eq(frame.timestamp + pd.Timedelta(hours=1)).all():
        raise ValueError("An hourly observation is available only at its interval end")
    counts = frame[["observation_count", "wind_speed_count", "temperature_count", "power_count"]]
    if not frame.training_eligible.eq(counts.eq(6).all(axis=1)).all():
        raise ValueError("Eligibility disagrees with coverage counts")
    valid = frame.loc[frame.training_eligible]
    if valid.empty or not np.isfinite(valid[["power_mean", "wind_speed_mean", "temperature_mean"]]).all().all():
        raise ValueError("Eligible observations must contain finite measurements")
    if not valid.power_mean.between(0, 1).all() or valid.wind_speed_mean.lt(0).any():
        raise ValueError("Eligible measurements violate physical bounds")


def load_history(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["timestamp", "available_at"])
    frame = local_history(frame)
    validate_history(frame)
    return frame


def training_before(frame: pd.DataFrame, origin) -> pd.DataFrame:
    frame = local_history(frame)
    origin = local_timestamp(origin)
    if origin > pd.Timestamp(TRAINING_CUTOFF):
        raise ValueError("Training origin exceeds January boundary")
    result = frame.loc[frame.training_eligible & frame.timestamp.lt(origin) & frame.available_at.le(origin)].copy()
    if result.empty:
        raise ValueError("No eligible past observations")
    return result


def weather_inputs(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[["timestamp", "wind_speed_mean", "temperature_mean"]].rename(
        columns={"wind_speed_mean": "wind_speed", "temperature_mean": "temperature"})


def forecast_pairs(frame: pd.DataFrame, start, end, horizon=48) -> pd.DataFrame:
    """Daily midnight origins, complete 48-hour windows inside [start, end).

    Horizon 1 labels [origin, origin+1h), so timestamp equals origin for hour 1.
    Missing target hours are omitted, not compressed into shorter lead times.
    The weather columns are explicitly observed-weather proxies.
    """
    frame = local_history(frame)
    start, end = local_timestamp(start), local_timestamp(end)
    if horizon not in (24, 48) or end > pd.Timestamp(TRAINING_CUTOFF) or start >= end:
        raise ValueError("Invalid proxy evaluation window")
    parts = []
    eligible = frame.loc[frame.training_eligible]
    for origin in pd.date_range(start, end - pd.Timedelta(hours=horizon), freq="D"):
        targets = pd.DataFrame({"timestamp": pd.date_range(origin, periods=horizon, freq="h"),
                                "forecast_origin": origin, "horizon_hour": np.arange(1, horizon + 1)})
        parts.append(targets.merge(eligible, on="timestamp", how="inner", validate="one_to_one"))
    if not parts:
        raise ValueError("Window too short for requested horizon")
    result = pd.concat(parts, ignore_index=True)
    if result.empty:
        raise ValueError("No eligible evaluation targets")
    return result
