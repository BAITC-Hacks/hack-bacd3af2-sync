"""Replay the single, already-standardized archive CSV exported by backend."""
import hashlib
from io import BytesIO
import json
import re
from pathlib import Path
import pandas as pd
from src.config import MODEL_DIR, TIMEZONE, WEATHER_COLUMNS, TRAINING_CUTOFF
from src.time_utils import local_timestamp, local_timestamps
from src.weather.schema import validate_weather
from src.inference.predict import predict_with_models

INPUT_COLUMNS = ["forecast_origin", "timestamp", "turbine_id", "wind_speed", "temperature",
                 "latitude", "longitude", "weather_valid_time", "weather_source"]
OUTPUT_COLUMNS = ["forecast_origin", "target_timestamp", "horizon_hours", "turbine_id",
                  "predicted_power", "wind_speed_forecast", "temperature_forecast", "model_version"]


def replay_csv(weather_path, output_dir, start="2026-01-31", end="2026-02-28",
               model_dir=MODEL_DIR, early_model_dir=MODEL_DIR / "asof_2026-01-31"):
    """Generate separate 24h/48h runs; horizon_hours is the one-based lead hour.

    Backend defines weather_valid_time as run_init + 6h availability. Parse
    run= from weather_source (explicit UTC) and record true weather lead times.
    """
    weather_path, output_dir = Path(weather_path), Path(output_dir)
    if output_dir.exists():
        raise ValueError("Use a new output directory; saved forecasts must not be overwritten")
    start, end = local_timestamp(start), local_timestamp(end)
    if pd.isna(start) or pd.isna(end) or start > end or start != start.normalize() or end != end.normalize():
        raise ValueError("Origin range must contain ascending midnight Asia/Almaty dates")
    if not weather_path.is_file():
        raise FileNotFoundError(f"Backend weather export is not available: {weather_path}")
    blob = weather_path.read_bytes()
    frame = pd.read_csv(BytesIO(blob))
    if len(frame.columns) != len(INPUT_COLUMNS) or set(frame.columns) != set(INPUT_COLUMNS):
        raise ValueError(f"Expected exactly the backend CSV columns: {INPUT_COLUMNS}")
    for column in ("forecast_origin", "timestamp", "weather_valid_time"):
        frame[column] = local_timestamps(frame[column])
        if frame[column].isna().any():
            raise ValueError(f"Missing {column}")
    if frame.weather_valid_time.gt(frame.forecast_origin).any():
        raise ValueError("Leakage guard: weather_valid_time is availability and must not follow forecast_origin")
    frame["turbine_id"] = pd.to_numeric(frame.turbine_id, errors="raise")
    if not frame.turbine_id.isin([1, 2]).all():
        raise ValueError("CSV turbine_id must be 1 or 2")
    frame["turbine_id"] = frame.turbine_id.astype(int)
    if frame.weather_source.isna().any() or frame.weather_source.astype(str).str.strip().eq("").any():
        raise ValueError("Missing weather_source provenance")
    run_times = {}
    for source in frame.weather_source.unique():
        match = re.search(r"(?:^|:)run=([^\s,;]+)$", str(source))
        if match is None:
            raise ValueError("weather_source must contain an explicit run=UTC timestamp")
        run = pd.Timestamp(match.group(1))
        if pd.isna(run) or run.tzinfo is None or run.utcoffset().total_seconds() != 0:
            raise ValueError("weather_source run= must specify UTC with Z or +00:00")
        # Explicit conversion of provider run metadata, never of turbine hours.
        run_times[source] = run.tz_convert(TIMEZONE).tz_localize(None)
    frame["weather_run_init"] = frame.weather_source.map(run_times)
    if not frame.weather_valid_time.eq(frame.weather_run_init + pd.Timedelta(hours=6)).all():
        raise ValueError("weather_valid_time must equal source run initialization + 6 hours")
    frame["weather_lead_hours"] = (frame.timestamp - frame.weather_run_init).dt.total_seconds() / 3600
    if frame.weather_lead_hours.lt(0).any():
        raise ValueError("Weather target precedes model run initialization")
    if frame.duplicated(["forecast_origin", "timestamp", "turbine_id"]).any():
        raise ValueError("Duplicate origin/target/turbine weather rows")
    expected = {(origin, turbine) for origin in pd.date_range(start, end, freq="D") for turbine in (1, 2)}
    actual = set(zip(frame.forecast_origin, frame.turbine_id))
    if actual != expected:
        raise ValueError(f"Origin coverage mismatch: {len(expected-actual)} missing, {len(actual-expected)} extra batches")
    prepared = []
    # Validate every 48-hour batch before running any model. No interpolation.
    for origin, turbine in sorted(expected):
        batch = frame.loc[frame.forecast_origin.eq(origin) & frame.turbine_id.eq(turbine)]
        weather, _ = validate_weather(turbine, batch[list(WEATHER_COLUMNS)], 48, origin)
        if batch.weather_source.nunique() != 1:
            raise ValueError("Each origin/turbine must use one archived run, not a stitched series")
        prepared.append((origin, turbine, weather, batch.sort_values("timestamp")))
    forecasts = {24: [], 48: []}
    batches = {24: [], 48: []}
    for origin, turbine, weather, archive in prepared:
        models = early_model_dir if origin < pd.Timestamp(TRAINING_CUTOFF) else model_dir
        if models is None:
            raise ValueError("January 31 requires a model trained before that origin")
        for horizon in (24, 48):
            prediction = predict_with_models(turbine, weather.iloc[:horizon].copy(), horizon, origin, models)
            batches[horizon].append({"forecast_origin": origin.isoformat(), "turbine_id": turbine,
                                     "weather_sources": archive.weather_source.unique().tolist(),
                                     "weather_run_init_local": archive.weather_run_init.iloc[0].isoformat(),
                                     "weather_available_at": archive.weather_valid_time.iloc[0].isoformat(),
                                     "weather_lead_hours_min": float(archive.weather_lead_hours.iloc[:horizon].min()),
                                     "weather_lead_hours_max": float(archive.weather_lead_hours.iloc[:horizon].max()),
                                     "model_version": prediction.model_version.iloc[0],
                                     "diagnostics": prediction.attrs["diagnostics"]})
            renamed = prediction.rename(columns={"timestamp": "target_timestamp", "horizon_hour": "horizon_hours",
                                                 "wind_speed": "wind_speed_forecast", "temperature": "temperature_forecast"})
            renamed = renamed[OUTPUT_COLUMNS]
            renamed.attrs = {}
            forecasts[horizon].append(renamed)
    results = {h: pd.concat(parts, ignore_index=True) for h, parts in forecasts.items()}
    output_dir.mkdir(parents=True)
    for horizon, result in results.items():
        folder = output_dir / f"{horizon}h"
        folder.mkdir()
        path = folder / "predictions.csv"
        result.to_csv(path, index=False)
        record = {"prediction_schema": "section_18", "timezone": TIMEZONE,
                  "forecast_window_hours": horizon, "horizon_hours_definition": "1-based interval lead: target_timestamp = origin + (horizon_hours - 1) hours",
                  "weather_csv": str(weather_path.resolve()), "weather_csv_sha256": hashlib.sha256(blob).hexdigest(),
                  "predictions_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                  "origin_start": start.isoformat(), "origin_end": end.isoformat(),
                  "prediction_rows": len(result), "data_kind": "backend_archived_forecast_contract",
                  "provenance_note": "Checked source run_init + 6h = weather_valid_time <= forecast_origin. Weather lead is measured from source run, not origin. Provider archive provenance comes from backend export.",
                  "batches": batches[horizon]}
        (folder / "run.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return results
