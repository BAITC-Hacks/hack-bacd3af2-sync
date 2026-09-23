"""Read-only diagnostics. Flags are evidence for review, never deletion rules."""
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd

from src.config import (
    CADENCE_MINUTES, CONSTANT_MIN_OBSERVATIONS, EXPECTED_END,
    EXPECTED_START, IQR_MULTIPLIER,
)
from src.data.load import NUMERIC_COLUMNS, load_raw, parse_raw


def missing_intervals(missing: pd.DatetimeIndex, cadence: pd.Timedelta) -> list[dict]:
    if missing.empty:
        return []
    series = pd.Series(missing)
    groups = series.diff().ne(cadence).cumsum()
    return [
        {"start": group.iloc[0].isoformat(), "end": group.iloc[-1].isoformat(),
         "missing_observations": len(group), "missing_minutes": len(group) * cadence.total_seconds() / 60}
        for _, group in series.groupby(groups)
    ]


def constant_runs(data: pd.DataFrame, column: str, cadence: pd.Timedelta,
                  minimum: int) -> list[dict]:
    # Ambiguous duplicate timestamps break a run instead of selecting a value.
    ordered = data.loc[data.timestamp.notna()].sort_values("timestamp")
    values = ordered[column]
    valid = np.isfinite(values) & ~ordered.timestamp.duplicated(keep=False)
    same = values.eq(values.shift()) & ordered.timestamp.diff().eq(cadence)
    groups = (~same | ~valid | ~valid.shift(fill_value=False)).cumsum()
    counts = groups[valid].value_counts()
    candidates = valid & groups.isin(counts[counts >= minimum].index)
    result = []
    for _, group in ordered.loc[candidates].groupby(groups[candidates]):
        if len(group) >= minimum:
            result.append({"start": group.timestamp.iloc[0].isoformat(),
                           "end": group.timestamp.iloc[-1].isoformat(),
                           "observations": len(group), "value": float(group[column].iloc[0])})
    return result


def audit_file(path: str | Path, turbine_id: int, *,
               expected_start: str = EXPECTED_START, expected_end: str = EXPECTED_END,
               cadence_minutes: int = CADENCE_MINUTES,
               constant_min_observations: int = CONSTANT_MIN_OBSERVATIONS) -> dict:
    if cadence_minutes <= 0 or constant_min_observations < 2:
        raise ValueError("Cadence must be positive and constant minimum must be at least 2")
    start, end = pd.Timestamp(expected_start), pd.Timestamp(expected_end)
    if start > end:
        raise ValueError("Expected start must not follow expected end")
    path = Path(path)
    raw = load_raw(path)
    data = parse_raw(raw)
    cadence = pd.Timedelta(minutes=cadence_minutes)
    times = pd.DatetimeIndex(data.timestamp.dropna().unique()).sort_values()
    grid = pd.date_range(start, end, freq=cadence)
    absent = grid.difference(times)
    gaps = missing_intervals(absent, cadence)
    deltas = times.to_series().diff().dropna().dt.total_seconds().div(60)
    input_times = data.timestamp.dropna()
    missing_tokens = {"", "nan", "na", "n/a", "null", "none"}
    source_missing = {c: int(raw[c].str.strip().str.lower().isin(missing_tokens).sum()) for c in raw}
    numeric = {}
    for column in NUMERIC_COLUMNS:
        values = data[column]
        finite = values[np.isfinite(values)]
        q1, q3 = (float(finite.quantile(q)) if len(finite) else None for q in (.25, .75))
        low = q1 - IQR_MULTIPLIER * (q3 - q1) if q1 is not None else None
        high = q3 + IQR_MULTIPLIER * (q3 - q1) if q3 is not None else None
        missing = raw[column].str.strip().str.lower().isin(missing_tokens)
        numeric[column] = {
            "min": float(finite.min()) if len(finite) else None,
            "max": float(finite.max()) if len(finite) else None,
            "mean": float(finite.mean()) if len(finite) else None,
            "nan_count": int(values.isna().sum()),
            "invalid_numeric_count": int((values.isna() & ~missing).sum()),
            "infinity_count": int(np.isinf(values).sum()),
            "iqr_lower_fence": low, "iqr_upper_fence": high,
            "iqr_outlier_count": int(((finite < low) | (finite > high)).sum()) if len(finite) else 0,
            "constant_runs": constant_runs(data, column, cadence, constant_min_observations),
        }
    valid = data.loc[data.timestamp.notna()]
    conflicting = valid.groupby("timestamp")[list(NUMERIC_COLUMNS)].nunique(dropna=False).gt(1).any(axis=1)
    monthly = valid.groupby(valid.timestamp.dt.strftime("%Y-%m")).size()
    duplicate_times = valid.timestamp.duplicated()
    return {
        "turbine_id": turbine_id, "source_file": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(raw), "columns": len(raw.columns),
        "raw_dtypes": {c: str(t) for c, t in raw.dtypes.items()},
        "parsed_dtypes": {c: str(t) for c, t in data.dtypes.items()},
        "period_start": times.min().isoformat() if len(times) else None,
        "period_end": times.max().isoformat() if len(times) else None,
        "expected_start": start.isoformat(), "expected_end": end.isoformat(),
        "timezone": "unspecified in source; no timezone conversion applied",
        "exact_duplicate_rows_extra": int(raw.duplicated().sum()),
        "duplicate_timestamps_extra": int(duplicate_times.sum()),
        "conflicting_timestamp_groups": int(conflicting.sum()),
        "invalid_or_missing_timestamps": int(data.timestamp.isna().sum()),
        "source_missing_counts": source_missing,
        "backward_timestamp_steps": int(input_times.diff().lt(pd.Timedelta(0)).sum()),
        "outside_expected_period_rows": int(((data.timestamp < start) | (data.timestamp > end)).sum()),
        "off_grid_rows": int((data.timestamp.notna() & ((data.timestamp - start) % cadence).ne(pd.Timedelta(0))).sum()),
        "expected_observations": len(grid), "observed_grid_timestamps": len(grid.intersection(times)),
        "missing_observations": len(absent), "missing_fraction": len(absent) / len(grid),
        "gap_count": len(gaps), "gaps": gaps,
        "timestamp_delta_minutes_distribution": {str(k): int(v) for k, v in deltas.value_counts().sort_index().items()},
        "observations_by_month": {k: int(v) for k, v in monthly.items()},
        "power_outside_0_1": int(((data.power < 0) | (data.power > 1)).sum()),
        "negative_wind_speed": int(data.wind_speed.lt(0).sum()),
        "numeric": numeric,
        "rules": {"cadence_minutes": cadence_minutes,
                  "constant_min_observations": constant_min_observations,
                  "outlier_iqr_multiplier": IQR_MULTIPLIER,
                  "cleaning": "none; all original rows preserved"},
    }
