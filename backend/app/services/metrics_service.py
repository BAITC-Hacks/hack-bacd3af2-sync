"""Model quality metrics for GET /api/metrics.

With the real model, scores come from the ML team's ml/models/turbine_N/metrics.json:
the hold-out block (`holdout.models[selected_model].overall`). Those are scores of the
power model on historical hours driven by *observed* weather (evaluation_kind
"observed_weather_proxy") — not operational forecast accuracy, which would also include
weather-forecast error. Anything missing or malformed falls back to demo values.
"""

import json
import logging
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from pydantic import ValidationError

from app.core.constants import TURBINES
from app.schemas.metrics import MetricsEvaluation, MetricsResponse, ModelMetrics

logger = logging.getLogger(__name__)

# Demo validation scores shown with the mock model or when real metrics are unavailable.
DEMO_METRICS: tuple[ModelMetrics, ...] = (
    ModelMetrics(turbine_id=1, mae=0.084, rmse=0.121, r2=0.78),
    ModelMetrics(turbine_id=2, mae=0.091, rmse=0.134, r2=0.74),
)

_EVALUATION_NOTES: dict[str, str] = {
    "observed_weather_proxy": (
        "Power-model scores on a hold-out period driven by observed weather. "
        "Not operational forecast accuracy: weather-forecast error is not included."
    ),
}


class MetricsFileError(ValueError):
    """A metrics.json file is missing or does not have the expected structure."""


def _read_turbine_metrics(path: Path, turbine_id: int) -> tuple[ModelMetrics, str, date, date]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        holdout = payload["holdout"]
        overall = holdout["models"][payload["selected_model"]]["overall"]
        metrics = ModelMetrics(
            turbine_id=turbine_id,
            mae=overall["mae"],
            rmse=overall["rmse"],
            r2=overall["r2"],
            n=overall.get("n"),
        )
        start = date.fromisoformat(str(holdout["start"])[:10])
        end = date.fromisoformat(str(holdout["end_exclusive"])[:10]) - timedelta(days=1)
        return metrics, str(payload["evaluation_kind"]), start, end
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError, ValidationError) as exc:
        raise MetricsFileError(f"{path}: {exc}") from exc


class MetricsService:
    def __init__(self, metrics_dir: Path | None, turbine_ids: Sequence[int] = tuple(TURBINES)) -> None:
        # None → the served model has no real metrics (mock adapter): always demo values.
        self._metrics_dir = metrics_dir
        self._turbine_ids = tuple(turbine_ids)

    def get_metrics(self) -> MetricsResponse:
        if self._metrics_dir is None:
            return self._demo()
        try:
            rows = [
                _read_turbine_metrics(self._metrics_dir / f"turbine_{turbine_id}" / "metrics.json", turbine_id)
                for turbine_id in self._turbine_ids
            ]
        except MetricsFileError as exc:
            logger.warning("Real model metrics unavailable, serving demo values: %s", exc)
            return self._demo()

        kinds = {kind for _, kind, _, _ in rows}
        kind = kinds.pop() if len(kinds) == 1 else "mixed"
        return MetricsResponse(
            models=[metrics for metrics, _, _, _ in rows],
            source="holdout",
            evaluation=MetricsEvaluation(
                kind=kind,
                period_start=min(start for _, _, start, _ in rows),
                period_end=max(end for _, _, _, end in rows),
                note=_EVALUATION_NOTES.get(kind, "Hold-out scores reported by the ML pipeline."),
            ),
        )

    @staticmethod
    def _demo() -> MetricsResponse:
        return MetricsResponse(models=list(DEMO_METRICS), source="demo")
