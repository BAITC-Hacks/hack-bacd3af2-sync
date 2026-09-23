"""Read frozen predictions and labels only after replay; never run fitting or inference."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.time_utils import local_history, local_timestamp
from src.training.evaluate import detailed_metrics


def evaluate(run_dir, actuals_path, output_path, start="2026-02-01", end="2026-03-01"):
    run_dir, actuals_path, output_path = Path(run_dir), Path(actuals_path), Path(output_path)
    if output_path.exists():
        raise ValueError("Evaluation output must be a new file")
    start, end = local_timestamp(start), local_timestamp(end)
    if pd.isna(start) or pd.isna(end) or start >= end:
        raise ValueError("Invalid evaluation interval")
    prediction_path = run_dir / "predictions.csv"
    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    if hashlib.sha256(prediction_path.read_bytes()).hexdigest() != record["predictions_sha256"]:
        raise ValueError("Frozen predictions were modified after replay")
    predictions = pd.read_csv(prediction_path)
    if record.get("prediction_schema") == "section_18":
        predictions = predictions.rename(columns={"target_timestamp": "timestamp", "horizon_hours": "horizon_hour",
                                                   "wind_speed_forecast": "wind_speed", "temperature_forecast": "temperature"})
    predictions = local_history(predictions)
    labels = local_history(pd.read_csv(actuals_path))
    if set(labels) != {"timestamp", "turbine_id", "power_mean"}:
        raise ValueError("Labels require exactly timestamp, turbine_id, power_mean; hourly complete observations only")
    if labels.timestamp.isna().any() or not labels.timestamp.eq(labels.timestamp.dt.floor("h")).all():
        raise ValueError("Invalid label timestamps")
    if labels.duplicated(["timestamp", "turbine_id"]).any():
        raise ValueError("Duplicate actual labels")
    if not labels.turbine_id.isin([1, 2]).all():
        raise ValueError("Invalid turbine_id in labels")
    labels["power_mean"] = pd.to_numeric(labels.power_mean, errors="raise")
    if not np.isfinite(labels.power_mean).all() or not labels.power_mean.between(0, 1).all():
        raise ValueError("Actual power labels must be finite and within [0,1]")
    if predictions.duplicated(["forecast_origin", "timestamp", "turbine_id"]).any():
        raise ValueError("Duplicate prediction keys")
    selected = predictions.loc[predictions.timestamp.ge(start) & predictions.timestamp.lt(end)]
    if selected.empty:
        raise ValueError("No predictions within evaluation target interval")
    scored = selected.merge(labels, on=["timestamp", "turbine_id"], how="left", validate="many_to_one", indicator=True)
    matched = scored.loc[scored._merge.eq("both")].copy()
    if matched.empty:
        raise ValueError("No matching actual labels; metrics are unavailable")
    result = {"target_start": start.isoformat(), "target_end_exclusive": end.isoformat(),
              "forecast_window_hours": record.get("forecast_window_hours", record.get("horizon_hours")),
              "predictions_sha256": record["predictions_sha256"],
              "actuals_sha256": hashlib.sha256(actuals_path.read_bytes()).hexdigest(),
              "prediction_pairs": len(selected), "scored_pairs": len(matched),
              "missing_label_pairs": len(scored) - len(matched),
              "excluded_prediction_pairs_outside_target_interval": len(predictions)-len(selected),
              "metric_weighting": "One observation per turbine/origin/target; overlapping targets count separately",
              "turbines": {}}
    for turbine, group in scored.groupby("turbine_id"):
        valid = group.loc[group._merge.eq("both")].rename(columns={"wind_speed": "wind_speed_mean"})
        result["turbines"][str(turbine)] = {"prediction_pairs": len(group), "scored_pairs": len(valid),
            "missing_label_pairs": len(group)-len(valid),
            "unique_scored_target_hours": valid.timestamp.nunique(),
            "metrics": detailed_metrics(valid, valid.predicted_power) if len(valid) else None}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--actuals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", default="2026-02-01")
    parser.add_argument("--end", default="2026-03-01")
    args = parser.parse_args()
    result = evaluate(args.run_dir, args.actuals, args.output, args.start, args.end)
    print(f"Scored {result['scored_pairs']} pairs; {result['missing_label_pairs']} pairs lack labels")


if __name__ == "__main__":
    main()
