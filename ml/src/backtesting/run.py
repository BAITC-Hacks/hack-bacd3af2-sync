"""Replay backend archived forecasts. This module never loads actual power labels."""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from src.config import ML_ROOT, MODEL_DIR, TIMEZONE, WEATHER_COLUMNS, TRAINING_CUTOFF
from src.time_utils import local_timestamp
from src.inference.predict import predict_with_models


def replay(manifest_path, output_dir, start="2026-01-31", end="2026-02-28", horizon=48,
           model_dir=MODEL_DIR, early_model_dir=None):
    start, end = local_timestamp(start), local_timestamp(end)
    if pd.isna(start) or pd.isna(end) or start > end or start != start.normalize() or end != end.normalize():
        raise ValueError("Replay origins must be valid midnight dates in ascending order")
    if horizon not in (24, 48):
        raise ValueError("Horizon must be 24 or 48")
    manifest_path, output_dir = Path(manifest_path), Path(output_dir)
    if output_dir.exists():
        raise ValueError("Use a new output directory to preserve previous forecast results")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("timezone") != TIMEZONE or manifest.get("data_kind") != "archived_forecast":
        raise ValueError("Manifest must declare Asia/Almaty archived_forecast data")
    if not isinstance(manifest.get("source"), str) or not manifest["source"].strip():
        raise ValueError("Missing weather source")
    batches = manifest.get("batches")
    if not isinstance(batches, list) or not batches:
        raise ValueError("Manifest has no batches")
    indexed = {}
    for batch in batches:
        turbine = batch.get("turbine_id")
        if type(turbine) is not int or turbine not in (1, 2):
            raise ValueError("Invalid turbine_id in manifest")
        origin = local_timestamp(batch.get("forecast_origin"))
        if pd.isna(origin):
            raise ValueError("Invalid manifest forecast_origin")
        key = (turbine, origin)
        if key in indexed:
            raise ValueError("Duplicate turbine/origin batch")
        indexed[key] = batch
    expected = {(i, origin) for origin in pd.date_range(start, end, freq="D") for i in (1, 2)}
    if set(indexed) != expected:
        raise ValueError(f"Manifest origin coverage mismatch: {len(expected-set(indexed))} missing, {len(set(indexed)-expected)} extra batches")
    forecasts, provenance = [], []
    for turbine, origin in sorted(expected, key=lambda key: (key[1], key[0])):
        batch = indexed[(turbine, origin)]
        issued = local_timestamp(batch.get("weather_run_available_at"))
        if pd.isna(issued) or issued > origin:
            raise ValueError("Leakage guard: weather run was not available at forecast_origin")
        root = manifest_path.resolve().parent
        path = (root / batch["file"]).resolve()
        if not path.is_relative_to(root) or path == manifest_path.resolve():
            raise ValueError("Weather file must be inside manifest directory")
        blob = path.read_bytes()
        fingerprint = hashlib.sha256(blob).hexdigest()
        if fingerprint != batch.get("sha256"):
            raise ValueError("Weather file SHA-256 mismatch")
        weather = pd.read_csv(path)
        if set(weather.columns) != set(WEATHER_COLUMNS) or len(weather.columns) != len(WEATHER_COLUMNS):
            raise ValueError("Replay accepts only weather contract columns, never actual power labels")
        models = model_dir
        if origin < pd.Timestamp(TRAINING_CUTOFF):
            if early_model_dir is None:
                raise ValueError("Pre-February origins require --early-model-dir trained before that origin")
            models = early_model_dir
        prediction = predict_with_models(turbine, weather, horizon, origin, models)
        provenance.append({"turbine_id": turbine, "forecast_origin": origin.isoformat(),
                           "weather_run_available_at": issued.isoformat(), "weather_file": batch["file"],
                           "weather_sha256": fingerprint, "model_version": prediction.model_version.iloc[0],
                           "diagnostics": prediction.attrs["diagnostics"]})
        prediction.attrs = {}
        forecasts.append(prediction)
    result = pd.concat(forecasts, ignore_index=True)
    output_dir.mkdir(parents=True)
    output = output_dir / "predictions.csv"
    result.to_csv(output, index=False, lineterminator="\n")
    record = {"timezone": TIMEZONE, "source": manifest["source"], "data_kind": "archived_forecast",
              "provenance_note": "Issue-time provenance is supplied by backend, not independently verified by ML",
              "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
              "predictions_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "start_origin": start.isoformat(), "end_origin": end.isoformat(), "horizon_hours": horizon,
              "prediction_rows": len(result), "batches": provenance}
    (output_dir / "run.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--manifest", type=Path, help="Legacy manifest input (optional)")
    inputs.add_argument("--weather", type=Path, help="Single backend CSV; defaults to repository data/weather/february_backtest.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--start", default="2026-01-31")
    parser.add_argument("--end", default="2026-02-28")
    parser.add_argument("--horizon", type=int, choices=(24, 48), help="Legacy manifest mode only; CSV always runs both 24h and 48h")
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--early-model-dir", type=Path, default=MODEL_DIR / "asof_2026-01-31")
    args = parser.parse_args()
    if args.manifest:
        result = replay(args.manifest, args.output_dir, args.start, args.end, args.horizon or 48, args.model_dir, args.early_model_dir)
        print(f"Saved {len(result)} forecasts. No actual labels were loaded.")
    else:
        if args.horizon:
            parser.error("CSV mode always generates both horizons; omit --horizon")
        from src.backtesting.csv_replay import replay_csv
        results = replay_csv(args.weather or ML_ROOT.parent / "data/weather/february_backtest.csv",
                             args.output_dir, args.start, args.end, args.model_dir, args.early_model_dir)
        for horizon, result in results.items():
            print(f"Saved {len(result)} forecasts for {horizon}h. No actual labels were loaded.")


if __name__ == "__main__":
    main()
