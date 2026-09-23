import json
import logging
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.schemas.metrics import MetricsResponse, ModelMetrics

logger = logging.getLogger(__name__)

# Demo validation scores shown until the ML part ships models/metrics.json.
DEMO_METRICS: tuple[ModelMetrics, ...] = (
    ModelMetrics(turbine_id=1, mae=0.084, rmse=0.121, r2=0.78),
    ModelMetrics(turbine_id=2, mae=0.091, rmse=0.134, r2=0.74),
)

_metrics_list = TypeAdapter(list[ModelMetrics])


class MetricsService:
    """Serves model quality metrics.

    Expected file format (written by the ML training pipeline):
        [{"turbine_id": 1, "mae": 0.08, "rmse": 0.12, "r2": 0.78}, ...]
    """

    def __init__(self, metrics_file: Path) -> None:
        self._metrics_file = metrics_file

    def get_metrics(self) -> MetricsResponse:
        if self._metrics_file.is_file():
            try:
                models = _metrics_list.validate_python(json.loads(self._metrics_file.read_text()))
                return MetricsResponse(models=models, source="file")
            except (OSError, json.JSONDecodeError, ValidationError) as exc:
                logger.warning("Ignoring invalid metrics file %s: %s", self._metrics_file, exc)
        return MetricsResponse(models=list(DEMO_METRICS), source="demo")
