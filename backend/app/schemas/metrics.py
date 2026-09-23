from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import TurbineId


class ModelMetrics(BaseModel):
    turbine_id: TurbineId
    mae: float = Field(ge=0)
    rmse: float = Field(ge=0)
    r2: float = Field(le=1)
    # Number of evaluated (origin, hour) pairs; None for demo values.
    n: int | None = Field(default=None, ge=0)


class MetricsEvaluation(BaseModel):
    """How the scores were obtained — shown next to them so they are not over-read."""

    kind: str  # e.g. "observed_weather_proxy"
    period_start: date
    period_end: date  # inclusive
    note: str


class MetricsResponse(BaseModel):
    models: list[ModelMetrics]
    # "holdout": real scores of the served CatBoost models; "demo": placeholders.
    source: Literal["demo", "holdout"]
    evaluation: MetricsEvaluation | None = None
