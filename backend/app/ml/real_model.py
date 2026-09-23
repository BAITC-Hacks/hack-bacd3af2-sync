"""Adapter for the real ML model delivered by the ML part.

The ML engineer provides `app/ml/predictor.py` exposing:

    def predict_power(
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame

plus `app/ml/features.py` and `models/turbine_{1,2}.cbm`. Enable it with MODEL_ADAPTER=real.
No changes to the agent, routes or frontend are needed.
"""

import asyncio
from datetime import datetime
from typing import Protocol

import pandas as pd

from app.ml.model_adapter import ModelAdapter, ModelUnavailableError


class PredictPowerFn(Protocol):
    def __call__(
        self,
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame: ...


class RealModelAdapter(ModelAdapter):
    name = "CatBoost"

    def __init__(self) -> None:
        try:
            from app.ml.predictor import predict_power  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ModelUnavailableError(
                "MODEL_ADAPTER=real, but app/ml/predictor.py with predict_power() is not available. "
                "Add the ML package or switch back to MODEL_ADAPTER=mock."
            ) from exc
        self._predict_power: PredictPowerFn = predict_power

    async def predict(
        self,
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame:
        # CatBoost inference is CPU-bound and synchronous: keep the event loop free.
        return await asyncio.to_thread(
            self._predict_power,
            turbine_id=turbine_id,
            weather=weather,
            horizon_hours=horizon_hours,
            forecast_origin=forecast_origin,
        )
