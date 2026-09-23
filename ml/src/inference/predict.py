"""Backend contract and CSV CLI. No weather requests and no model fitting."""
import argparse
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import MODEL_DIR, TIMEZONE, LOW_WIND_SANITY_MPS, HIGH_POWER_AT_LOW_WIND
from src.features.build_features import build_features
from src.inference.artifacts import get_model
from src.training.models import checked_prediction
from src.weather.schema import validate_weather

logger = logging.getLogger(__name__)
OUTPUT_COLUMNS = ["forecast_origin", "timestamp", "turbine_id", "horizon_hour",
                  "wind_speed", "temperature", "predicted_power", "model_version"]


def predict_power(turbine_id: int, weather: pd.DataFrame, horizon_hours: int,
                  forecast_origin: datetime) -> pd.DataFrame:
    return predict_with_models(turbine_id, weather, horizon_hours, forecast_origin,
                               os.environ.get("TURBINE_MODEL_DIR", str(MODEL_DIR)))


def predict_with_models(turbine_id, weather, horizon_hours, forecast_origin, model_dir):
    """Explicit model directory for replay; does not mutate process environment."""
    frame, origin = validate_weather(turbine_id, weather, horizon_hours, forecast_origin)
    bundle = get_model(turbine_id, model_dir)
    if origin < bundle.available_at:
        raise ValueError(f"Leakage guard: model contains observations available at {bundle.available_at}; "
                         f"it cannot forecast from earlier origin {origin}")
    features = build_features(frame).loc[:, list(bundle.features)]
    predicted, corrections = checked_prediction(bundle.model, features)
    # Diagnostic only: neither zero-wind nor unusual temperatures overwrite predictions.
    low_wind_high_power = int(((frame.wind_speed < LOW_WIND_SANITY_MPS) & (predicted > HIGH_POWER_AT_LOW_WIND)).sum())
    diagnostics = {**corrections, "low_wind_high_power_rows": low_wind_high_power}
    if any(diagnostics.values()):
        logger.warning("Turbine %s origin %s prediction diagnostics: %s", turbine_id, origin, diagnostics)
    result = pd.DataFrame({"forecast_origin": origin, "timestamp": frame.timestamp,
                           "turbine_id": int(turbine_id), "horizon_hour": np.arange(1, horizon_hours + 1),
                           "wind_speed": frame.wind_speed, "temperature": frame.temperature,
                           "predicted_power": predicted, "model_version": bundle.version})
    result = result[OUTPUT_COLUMNS]
    result.attrs.update(timezone=TIMEZONE, diagnostics=diagnostics,
                        weather_provenance="Backend must supply forecasts available at forecast_origin")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--turbine", type=int, choices=(1, 2), required=True)
    parser.add_argument("--weather", type=Path, required=True)
    parser.add_argument("--horizon", type=int, choices=(24, 48), required=True)
    parser.add_argument("--forecast-origin", help="Asia/Almaty local clock time; defaults to the batch origin")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frame = pd.read_csv(args.weather)
    if not args.forecast_origin and ("forecast_origin" not in frame or frame.empty):
        parser.error("Supply --forecast-origin or a nonempty weather forecast_origin column")
    origin = args.forecast_origin or frame.forecast_origin.iloc[0]
    result = predict_power(args.turbine, frame, args.horizon, origin)
    diagnostics_path = args.output.with_suffix(args.output.suffix + ".diagnostics.json")
    if args.output.resolve() == args.weather.resolve() or diagnostics_path.resolve() == args.weather.resolve():
        parser.error("Output must not overwrite the weather input")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    diagnostics_path.write_text(json.dumps(result.attrs, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(result)} hourly predictions to {args.output}")


if __name__ == "__main__":
    main()
