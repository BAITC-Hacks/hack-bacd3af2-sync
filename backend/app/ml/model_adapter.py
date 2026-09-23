"""The single seam between the backend and the ML part.

Mirrors the agreed ML contract:

    predict_power(turbine_id, weather, horizon_hours, forecast_origin) -> pd.DataFrame

weather columns:  timestamp, wind_speed, temperature, forecast_origin, latitude, longitude
output columns:   forecast_origin, timestamp, turbine_id, horizon_hour,
                  wind_speed, temperature, predicted_power, model_version
"""

from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd


class ModelUnavailableError(RuntimeError):
    """Raised when the configured model cannot be loaded."""


class ModelAdapter(ABC):
    #: Human-readable name shown in agent step messages.
    name: str

    @abstractmethod
    async def predict(
        self,
        turbine_id: int,
        weather: pd.DataFrame,
        horizon_hours: int,
        forecast_origin: datetime,
    ) -> pd.DataFrame:
        """Return an hourly power forecast shaped exactly like the ML contract output."""
