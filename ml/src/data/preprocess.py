"""Conservative hourly aggregation. Never interpolate or learn cleaning thresholds."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import EXPECTED_START, EXPECTED_END, RAW_DIR, PROCESSED_DIR, REPORT_DIR
from src.data.load import load_raw, parse_raw, NUMERIC_COLUMNS
from src.time_utils import local_history, local_timestamp
from src.config import TIMEZONE


def aggregate_hourly(data: pd.DataFrame, turbine_id: int, *,
                     start: str = EXPECTED_START, end: str = EXPECTED_END) -> tuple[pd.DataFrame, dict]:
    """Return all hours and an accounting of exclusions; input is never mutated.

    Each timestamp labels the start of [timestamp, timestamp + 1 hour).
    Its aggregate is available only at available_at, the interval end.
    Duplicate valid timestamps fail closed, including identical duplicates.
    """
    if turbine_id not in (1, 2):
        raise ValueError("turbine_id must be 1 or 2")
    data = local_history(data)
    first, last = local_timestamp(start), local_timestamp(end)
    if first > last or first != first.floor("h") or last != last.floor("h") + pd.Timedelta(minutes=50):
        raise ValueError("Study bounds must include complete hours (start :00, end :50)")
    if data.timestamp.dropna().duplicated().any():
        raise ValueError("Duplicate timestamps require an explicit upstream resolution policy")
    frame = data.copy()
    valid_time = frame.timestamp.notna()
    in_period = frame.timestamp.between(first, last)
    on_grid = ((frame.timestamp - first) % pd.Timedelta(minutes=10)).eq(pd.Timedelta(0))
    accepted = valid_time & in_period & on_grid
    summary = {"turbine_id": turbine_id, "timezone": TIMEZONE, "input_rows": len(frame),
               "invalid_timestamp_rows": int((~valid_time).sum()),
               "outside_period_rows": int((valid_time & ~in_period).sum()),
               "off_grid_rows_in_period": int((valid_time & in_period & ~on_grid).sum()),
               "accepted_timestamp_rows": int(accepted.sum()), "masked_cells": {}}
    frame = frame.loc[accepted].copy()
    for column in NUMERIC_COLUMNS:
        invalid = ~np.isfinite(frame[column])
        if column == "wind_speed":
            invalid |= frame[column].lt(0)
        elif column == "power":
            invalid |= ~frame[column].between(0, 1)
        summary["masked_cells"][column] = int(invalid.sum())
        frame.loc[invalid, column] = np.nan
    frame = frame.set_index("timestamp").sort_index()
    groups = frame.resample("h", closed="left", label="left")
    hourly = groups.agg(
        wind_speed_mean=("wind_speed", "mean"), wind_speed_std=("wind_speed", "std"),
        wind_speed_min=("wind_speed", "min"), wind_speed_max=("wind_speed", "max"),
        temperature_mean=("temperature", "mean"), temperature_std=("temperature", "std"),
        power_mean=("power", "mean"), wind_speed_count=("wind_speed", "count"),
        temperature_count=("temperature", "count"), power_count=("power", "count"),
    )
    hourly["observation_count"] = groups.size()
    hourly = hourly.reindex(pd.date_range(first, last.floor("h"), freq="h", name="timestamp"))
    counts = ["observation_count", "wind_speed_count", "temperature_count", "power_count"]
    hourly[counts] = hourly[counts].fillna(0).astype(int)
    hourly["coverage_fraction"] = hourly.observation_count / 6
    hourly["training_eligible"] = hourly[counts].eq(6).all(axis=1)
    hourly["turbine_id"] = turbine_id
    hourly["available_at"] = hourly.index + pd.Timedelta(hours=1)
    summary.update({"hours": len(hourly), "empty_hours": int(hourly.observation_count.eq(0).sum()),
                    "partial_hours": int(hourly.observation_count.between(1, 5).sum()),
                    "full_observation_hours": int(hourly.observation_count.eq(6).sum()),
                    "training_eligible_hours": int(hourly.training_eligible.sum()),
                    "start": first.isoformat(), "end": last.isoformat()})
    return hourly.reset_index(), summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turbine-1", type=Path, default=RAW_DIR / "turbine 1.csv")
    parser.add_argument("--turbine-2", type=Path, default=RAW_DIR / "turbine 2.csv")
    parser.add_argument("--output-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    for turbine, path in enumerate((args.turbine_1, args.turbine_2), 1):
        hourly, summary = aggregate_hourly(parse_raw(load_raw(path)), turbine)
        summary["source_file"] = path.name
        summary["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        hourly.to_csv(args.output_dir / f"turbine_{turbine}_hourly.csv", index=False)
        summaries.append(summary)
        print(f"Turbine {turbine}: {summary['hours']} hours, {summary['training_eligible_hours']} eligible")
    (args.report_dir / "preprocessing.json").write_text(json.dumps({"schema_version": 1, "turbines": summaries}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
