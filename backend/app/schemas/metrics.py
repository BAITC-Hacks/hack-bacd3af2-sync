from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import TurbineId


class ModelMetrics(BaseModel):
    turbine_id: TurbineId
    mae: float = Field(ge=0)
    rmse: float = Field(ge=0)
    r2: float = Field(le=1)


class MetricsResponse(BaseModel):
    models: list[ModelMetrics]
    # "demo" until the ML part ships models/metrics.json with real validation scores.
    source: Literal["demo", "file"]
