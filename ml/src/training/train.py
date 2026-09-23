"""Select on earlier windows, evaluate frozen selection on holdout, refit through January."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from src.config import PROCESSED_DIR, REPORT_DIR, MODEL_DIR, SELECTION_WINDOWS, HOLDOUT_WINDOW, TRAINING_CUTOFF
from src.config import TIMEZONE, WEATHER_PROVIDER, WEATHER_COLUMNS
from src.features.build_features import build_features
from src.training.validation import load_history, training_before, forecast_pairs, weather_inputs
from src.training.baselines import historical_baselines
from src.training.models import CANDIDATES, create_model, feature_names, parameters, checked_prediction, save_model, load_model
from src.training.evaluate import detailed_metrics


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def evaluate_window(history, start, end, names, label):
    train = training_before(history, start)
    pairs = forecast_pairs(history, start, end)
    x_train = build_features(weather_inputs(train))
    x_eval = build_features(weather_inputs(pairs))
    predictions, baseline_notes = historical_baselines(history, pairs)
    postprocessing = {name: {"clipped_below_zero": 0, "clipped_above_one": 0} for name in predictions}
    for name in names:
        print(f"  {label}: fitting {name} on {len(train)} hours", flush=True)
        model = create_model(name)
        columns = feature_names(name)
        with threadpool_limits(limits=4):
            model.fit(x_train[columns], train.power_mean)
            predictions[name], postprocessing[name] = checked_prediction(model, x_eval[columns])
    result = {"label": label, "start": str(start), "end_exclusive": str(end),
              "train_start": train.timestamp.min().isoformat(), "train_last_target": train.timestamp.max().isoformat(),
              "train_last_available_at": train.available_at.max().isoformat(), "train_rows": len(train),
              "evaluation_pairs": len(pairs), "unique_target_hours": pairs.timestamp.nunique(),
              "origins": pairs.forecast_origin.nunique(), "baseline_notes": baseline_notes,
              "models": {name: {**detailed_metrics(pairs, pred), "postprocessing": postprocessing[name]}
                         for name, pred in predictions.items()}}
    export = pairs[["forecast_origin", "timestamp", "horizon_hour", "power_mean", "wind_speed_mean", "temperature_mean"]].copy()
    export["window"] = label
    for name, pred in predictions.items():
        export[name] = pred
    return result, export


def train_turbine(turbine, data_dir, model_dir, report_dir):
    source = data_dir / f"turbine_{turbine}_hourly.csv"
    history = load_history(source)
    if "turbine_id" not in history or not history.turbine_id.eq(turbine).all():
        raise ValueError("Turbine identity mismatch")
    selection, exports = [], []
    for start, end in SELECTION_WINDOWS:
        result, predictions = evaluate_window(history, start, end, CANDIDATES, f"selection_{start[:7]}")
        selection.append(result)
        exports.append(predictions)
    scores = {name: float(np.mean([fold["models"][name]["overall"]["mae"] for fold in selection])) for name in CANDIDATES}
    winner = min(CANDIDATES, key=lambda name: scores[name])
    print(f"Turbine {turbine}: selected {winner}, mean rolling MAE {scores[winner]:.6f}", flush=True)
    # Selection is finalized before holdout evaluation. Do not reselect on its results.
    holdout_names = tuple(dict.fromkeys(("power_curve", winner)))
    holdout, predictions = evaluate_window(history, *HOLDOUT_WINDOW, holdout_names, "holdout")
    exports.append(predictions)
    final_train = training_before(history, TRAINING_CUTOFF)
    x = build_features(weather_inputs(final_train))[feature_names(winner)]
    model = create_model(winner)
    with threadpool_limits(limits=4):
        model.fit(x, final_train.power_mean)
    folder = model_dir / f"turbine_{turbine}"
    folder.mkdir(parents=True, exist_ok=True)
    path = save_model(model, winner, folder)
    reloaded = load_model(winner, path)
    probe = x.iloc[np.linspace(0, len(x)-1, min(128, len(x))).astype(int)]
    np.testing.assert_allclose(model.predict(probe), reloaded.predict(probe), rtol=1e-10, atol=1e-10)
    all_metrics = {"evaluation_kind": "observed_weather_proxy", "selection": selection,
                   "selection_mean_mae": scores, "selected_model": winner, "holdout": holdout}
    write_json(folder / "metrics.json", all_metrics)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    model_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata = {"schema_version": 1, "turbine_id": turbine, "model_type": winner,
                "model_file": path.name, "model_version": f"{winner}-{model_hash[:12]}",
                "artifact_sha256": model_hash, "dataset_sha256": digest,
                "training_start": final_train.timestamp.min().isoformat(),
                "training_end": final_train.timestamp.max().isoformat(),
                "training_last_available_at": final_train.available_at.max().isoformat(),
                "training_cutoff_exclusive": TRAINING_CUTOFF, "training_rows": len(final_train),
                "features": feature_names(winner), "target": "power_mean", "parameters": parameters(winner),
                "created_at": datetime.now(timezone.utc).isoformat(), "python_version": platform.python_version(),
                "package_versions": {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "catboost", "scikit-learn", "scipy", "joblib")},
                "evaluation_kind": "observed_weather_proxy", "timezone": TIMEZONE,
                "timestamp_representation": "Asia/Almaty wall-clock; no UTC conversion",
                "weather_provider": WEATHER_PROVIDER, "weather_input_columns": list(WEATHER_COLUMNS),
                "selection_rule": "Lowest equally weighted mean MAE across three pre-holdout windows",
                "selection_mean_mae": scores, "holdout_metrics": holdout["models"][winner]["overall"],
                "serialization_roundtrip_verified": True, "postprocessing": "clip [0,1] and count corrections",
                "limitations": ["No archived weather forecasts: scores are not operational forecasting accuracy",
                                "Final model includes holdout history; holdout score belongs to the pre-holdout fit",
                                "No February data read or used; no lag features"]}
    if winner.startswith("catboost"):
        metadata["feature_importance"] = dict(zip(feature_names(winner), model.feature_importances_.tolist()))
    write_json(folder / "metadata.json", metadata)
    report_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(exports, ignore_index=True).to_csv(report_dir / f"turbine_{turbine}_validation_predictions.csv.gz", index=False, compression="gzip")
    return metadata, all_metrics


def report(results, report_dir):
    lines = ["# Model comparison", "", "## Scope", "",
             "These are observed-weather proxy experiments, not operational weather-forecast backtests. All inputs and targets are before February 2026. February data is rejected, not silently filtered.", "",
             "## Validation protocol", "",
             "- Selection windows: June, September and November 2025, each trained only on complete hours available before its first origin. Models remain frozen within each window.",
             "- Choose the lowest equally weighted mean window MAE among power curve, histogram boosting, CatBoost weather-only and CatBoost with calendar features. Fixed parameters; no random holdout or early-stopping split.",
             "- Freeze the choice before checking December 2025 through January 2026. This holdout model trains only through November 30. Final saved models are then refit through January 31; their training fit is not the reported holdout score.",
             "- Daily midnight origins have 48 hourly intervals entirely within each window. Horizon 1 labels [origin, origin+1h); the timestamp is the interval start. Origins too near the window end are excluded.",
             "- Scores use common eligible target pairs. Overlapping target timestamps count separately for each origin; pair counts and unique target counts are retained in metrics.json. Missing hours keep their true lead times.",
             "- Persistence uses last complete power available at origin. Seasonal persistence repeats the previous day's 24-hour profile across both days; missing slots use persistence, with fallback counts recorded.",
             "- Model features use only wind, temperature and calendar transformations. No future observed within-hour statistics or power lags. Actual target-hour weather is an explicitly labeled proxy, not claimed to be available at origin.",
             "- MAE and RMSE use normalized power units. Normalized MAE divides by rated normalized capacity 1. R² is unavailable for constant targets. No MAPE.", ""]
    for metadata, metrics in results:
        turbine = metadata["turbine_id"]
        lines += [f"## Turbine {turbine}", "", f"Selected **{metadata['model_type']}**, version `{metadata['model_version']}`. Final fit: {metadata['training_rows']:,} complete hours.", "",
                  "| Candidate | Mean selection MAE |", "| --- | ---: |"]
        for name, score in sorted(metrics["selection_mean_mae"].items(), key=lambda item: item[1]):
            lines.append(f"| {name} | {score:.6f} |")
        lines += ["", "### Untouched holdout results", "", "| Model | MAE | RMSE | R² | Pairs |", "| --- | ---: | ---: | ---: | ---: |"]
        for name, record in metrics["holdout"]["models"].items():
            m = record["overall"]
            r2 = f"{m['r2']:.6f}" if m["r2"] is not None else "unavailable"
            lines.append(f"| {name} | {m['mae']:.6f} | {m['rmse']:.6f} | {r2} | {m['n']} |")
        h = metrics["holdout"]
        lines += ["", f"Holdout uses {h['origins']} origins and {h['unique_target_hours']} unique target hours. Seasonal fallback rows: {h['baseline_notes']['seasonal_fallback_rows']}; maximum persistence staleness: {h['baseline_notes']['persistence_max_staleness_hours']:.1f} hours.", "",
                  f"Full per-window, per-horizon, wind-bin and clipping diagnostics: `../models/turbine_{turbine}/metrics.json`. Reproducible prediction pairs: `turbine_{turbine}_validation_predictions.csv.gz`.", ""]
    lines += ["## Weather integration", "", "History and backend weather use Asia/Almaty clock hours without UTC conversion. Backend supplies real archived Open-Meteo forecasts, already mapped to wind_speed and temperature. ML does not fetch weather or interpret wind-height fields. Existing scores still use observed-weather proxies; archived forecasts have not been evaluated in this training run.", "",
              "## Remaining work", "", "Saved artifacts passed prediction round-trip checks. Backend predict_power input validation, model caching and archived-weather backtesting remain a separate stage. Separate turbine fits are compared with baselines here; a pooled turbine model has not been tested, so superiority over pooling is not established.", ""]
    (report_dir / "model_comparison.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turbine", choices=("1", "2", "all"), default="all")
    parser.add_argument("--data-dir", type=Path, default=PROCESSED_DIR)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--report-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()
    results = [train_turbine(i, args.data_dir, args.model_dir, args.report_dir)
               for i in ((1, 2) if args.turbine == "all" else (int(args.turbine),))]
    report(results, args.report_dir)
    print("Training, holdout evaluation and artifact checks complete.", flush=True)


if __name__ == "__main__":
    main()
