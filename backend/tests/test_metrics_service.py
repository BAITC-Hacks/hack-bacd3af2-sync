"""GET /api/metrics data: real hold-out scores from the ML team, demo fallback otherwise."""

import json
import shutil
from datetime import date
from pathlib import Path

import pytest

from app.core.config import REPO_ROOT
from app.services.metrics_service import DEMO_METRICS, MetricsService

MODEL_DIR = REPO_ROOT / "ml" / "models"
needs_artifacts = pytest.mark.skipif(
    not (MODEL_DIR / "turbine_1" / "metrics.json").is_file(), reason="ML metrics not present in ml/models"
)


def _overall(turbine_id: int) -> dict[str, float]:
    payload = json.loads((MODEL_DIR / f"turbine_{turbine_id}" / "metrics.json").read_text())
    return payload["holdout"]["models"][payload["selected_model"]]["overall"]


@needs_artifacts
def test_real_holdout_metrics_are_served_with_their_evaluation_context() -> None:
    response = MetricsService(MODEL_DIR).get_metrics()

    assert response.source == "holdout"
    for metrics in response.models:
        expected = _overall(metrics.turbine_id)
        assert (metrics.mae, metrics.rmse, metrics.r2, metrics.n) == (
            expected["mae"],
            expected["rmse"],
            expected["r2"],
            expected["n"],
        )
    evaluation = response.evaluation
    assert evaluation is not None
    assert evaluation.kind == "observed_weather_proxy"
    assert (evaluation.period_start, evaluation.period_end) == (date(2025, 12, 1), date(2026, 1, 31))
    assert "Not operational forecast accuracy" in evaluation.note


def test_mock_model_gets_demo_metrics() -> None:
    response = MetricsService(None).get_metrics()
    assert response.source == "demo" and response.evaluation is None
    assert response.models == list(DEMO_METRICS)


def test_missing_metrics_dir_falls_back_to_demo(tmp_path: Path) -> None:
    assert MetricsService(tmp_path / "nope").get_metrics().source == "demo"


@needs_artifacts
def test_one_missing_turbine_file_falls_back_to_demo_for_all(tmp_path: Path) -> None:
    shutil.copytree(MODEL_DIR / "turbine_1", tmp_path / "turbine_1")
    assert MetricsService(tmp_path).get_metrics().source == "demo"


@pytest.mark.parametrize("content", ["not json", json.dumps({"holdout": {}}), json.dumps({"selected_model": "x"})])
def test_malformed_metrics_fall_back_to_demo(tmp_path: Path, content: str) -> None:
    for turbine_id in (1, 2):
        folder = tmp_path / f"turbine_{turbine_id}"
        folder.mkdir()
        (folder / "metrics.json").write_text(content)
    assert MetricsService(tmp_path).get_metrics().source == "demo"
