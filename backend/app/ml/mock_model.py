"""Physics-flavoured stand-in for the CatBoost model.

Produces a DataFrame with exactly the contract columns so the rest of the system
behaves identically once RealModelAdapter is switched on.
"""

from datetime import datetime

import numpy as np
import pandas as pd

from app.core.constants import (
    CUT_IN_WIND_SPEED,
    CUT_OUT_WIND_SPEED,
    POWER_MAX,
    POWER_MIN,
    PREDICTION_COLUMNS,
)
from app.ml.model_adapter import ModelAdapter

MODEL_VERSION = "mock-sigmoid-v1"

# Per-turbine power curve: (wind speed at 50% output, curve width), m/s.
_POWER_CURVES: dict[int, tuple[float, float]] = {
    1: (7.6, 1.35),
    2: (8.0, 1.45),
}
_REFERENCE_TEMPERATURE_C = 15.0
_AIR_DENSITY_SENSITIVITY = 0.0035  # +0.35% output per °C below reference
_NOISE_STD = 0.02


class MockModelAdapter(ModelAdapter):
    name = "Mock power-curve"

    async def predict(
        self,
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame:
        frame = weather.sort_values("timestamp").head(horizon_hours).reset_index(drop=True)
        wind = frame["wind_speed"].to_numpy(dtype=float)
        temperature = frame["temperature"].to_numpy(dtype=float)
        timestamps = pd.to_datetime(frame["timestamp"])

        midpoint, width = _POWER_CURVES.get(turbine_id, _POWER_CURVES[1])
        curve = 1.0 / (1.0 + np.exp(-(wind - midpoint) / width))
        curve = np.where(wind < CUT_IN_WIND_SPEED, curve * (wind / CUT_IN_WIND_SPEED) ** 2, curve)
        curve = np.where(wind >= CUT_OUT_WIND_SPEED, 0.0, curve)

        air_density = 1.0 + _AIR_DENSITY_SENSITIVITY * (_REFERENCE_TEMPERATURE_C - temperature)
        diurnal = 1.0 + 0.02 * np.sin(2 * np.pi * (timestamps.dt.hour.to_numpy() - 3.0) / 24.0)
        rng = np.random.default_rng(forecast_origin.toordinal() * 100 + turbine_id)
        noise = rng.normal(0.0, _NOISE_STD, len(frame))

        power = np.clip(curve * air_density * diurnal + noise, POWER_MIN, POWER_MAX)
        horizon_hour = ((timestamps - pd.Timestamp(forecast_origin)) / pd.Timedelta(hours=1)).astype(int)

        result = pd.DataFrame(
            {
                "forecast_origin": pd.Timestamp(forecast_origin),
                "timestamp": timestamps,
                "turbine_id": turbine_id,
                "horizon_hour": horizon_hour,
                "wind_speed": wind,
                "temperature": temperature,
                "predicted_power": power.round(4),
                "model_version": MODEL_VERSION,
            }
        )
        return result.loc[:, list(PREDICTION_COLUMNS)]
