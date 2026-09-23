"""RealModelAdapter against the ML team's real artifacts in ml/models (no network)."""

import asyncio
import json
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from app.core.config import REPO_ROOT
from app.core.constants import PREDICTION_COLUMNS

pytest.importorskip("catboost", reason="ML inference stack not installed (pip install -r requirements-ml.txt)")

ML_DIR = REPO_ROOT / "ml"
MODEL_DIR = ML_DIR / "models"
ASOF_DIR = MODEL_DIR / "asof_2026-01-31"
if not (MODEL_DIR / "turbine_1" / "metadata.json").is_file():
    pytest.skip("ML model artifacts not present in ml/models", allow_module_level=True)

from app.agent.forecast_agent import ForecastAgent  # noqa: E402
from app.ml.model_adapter import ModelPredictionError, ModelUnavailableError  # noqa: E402
from app.ml.real_model import RealModelAdapter  # noqa: E402
from app.schemas.forecast import ForecastRequest  # noqa: E402
from app.services.weather_service import MockWeatherProvider, WeatherService  # noqa: E402

JAN_31 = datetime(2026, 1, 31)
FEB_01 = datetime(2026, 2, 1)


def _version(root: Path, turbine_id: int) -> str:
    return json.loads((root / f"turbine_{turbine_id}" / "metadata.json").read_text())["model_version"]


@pytest.fixture(scope="module")
def adapter() -> RealModelAdapter:
    return RealModelAdapter(model_dir=MODEL_DIR, ml_package_dir=ML_DIR)


def _weather(turbine_id: int, origin: datetime, hours: int = 48) -> pd.DataFrame:
    batch = asyncio.run(WeatherService(MockWeatherProvider()).get_weather([turbine_id], origin, hours))
    return batch.frames[turbine_id]


def test_loads_main_and_asof_bundles_with_metadata_versions(adapter: RealModelAdapter) -> None:
    for turbine_id in (1, 2):
        loaded = {bundle.root: bundle.version for bundle in adapter.bundles[turbine_id]}
        assert loaded == {MODEL_DIR: _version(MODEL_DIR, turbine_id), ASOF_DIR: _version(ASOF_DIR, turbine_id)}


@pytest.mark.parametrize(
    ("origin", "expected_root"),
    [
        (JAN_31, ASOF_DIR),  # main models were trained on Jan 31 itself → leakage
        (FEB_01, MODEL_DIR),
        (datetime(2026, 2, 28), MODEL_DIR),
    ],
)
def test_selects_newest_bundle_trained_strictly_before_origin(
    adapter: RealModelAdapter, origin: datetime, expected_root: Path
) -> None:
    for turbine_id in (1, 2):
        bundle = adapter.select_bundle(turbine_id, origin)
        assert bundle.root == expected_root
        assert bundle.available_at <= pd.Timestamp(origin)


def test_origin_before_every_bundle_is_rejected(adapter: RealModelAdapter) -> None:
    with pytest.raises(ModelPredictionError, match="trained strictly before origin"):
        adapter.select_bundle(1, datetime(2026, 1, 30))


@pytest.mark.parametrize("horizon", [24, 48])
def test_prediction_matches_backend_contract(adapter: RealModelAdapter, horizon: int) -> None:
    frame = asyncio.run(adapter.predict(1, _weather(1, FEB_01, horizon), horizon, FEB_01))

    assert list(frame.columns) == list(PREDICTION_COLUMNS)
    assert len(frame) == horizon
    assert frame["timestamp"].iloc[0] == pd.Timestamp(FEB_01)
    assert (frame["timestamp"].diff().dropna() == pd.Timedelta(hours=1)).all()
    assert frame["timestamp"].dt.tz is None  # naive Asia/Almaty wall clock, like the backend
    assert frame["predicted_power"].between(0, 1).all() and frame["predicted_power"].notna().all()
    assert set(frame["model_version"]) == {_version(MODEL_DIR, 1)}
    assert set(frame["turbine_id"]) == {1}


def test_january_31_is_served_by_the_asof_model(adapter: RealModelAdapter) -> None:
    frame = asyncio.run(adapter.predict(2, _weather(2, JAN_31), 48, JAN_31))
    assert set(frame["model_version"]) == {_version(ASOF_DIR, 2)}


def test_ml_loader_itself_refuses_the_main_model_on_january_31() -> None:
    """Second line of defence: even if selection were wrong, the ML guard blocks the leak."""
    from app.ml.predictor import predict_with_models

    with pytest.raises(ValueError, match="Leakage guard"):
        predict_with_models(1, _weather(1, JAN_31), 48, JAN_31, str(MODEL_DIR))


def test_invalid_weather_becomes_a_clear_prediction_error(adapter: RealModelAdapter) -> None:
    short = _weather(1, FEB_01).head(30)  # neither 24 nor 48 hours
    with pytest.raises(ModelPredictionError, match="Turbine 1"):
        asyncio.run(adapter.predict(1, short, 48, FEB_01))


def test_missing_model_dir_fails_fast_with_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ModelUnavailableError, match="does not exist"):
        RealModelAdapter(model_dir=tmp_path / "nope", ml_package_dir=ML_DIR)


def test_missing_ml_package_fails_fast_with_clear_error(tmp_path: Path) -> None:
    with pytest.raises(ModelUnavailableError, match="ML package not found"):
        RealModelAdapter(model_dir=MODEL_DIR, ml_package_dir=tmp_path)


def test_corrupted_model_file_fails_fast(tmp_path: Path) -> None:
    for turbine_id in (1, 2):
        shutil.copytree(MODEL_DIR / f"turbine_{turbine_id}", tmp_path / f"turbine_{turbine_id}")
    model_file = tmp_path / "turbine_1" / "model.cbm"
    model_file.write_bytes(model_file.read_bytes() + b"tampered")
    with pytest.raises(ModelUnavailableError, match="SHA-256 mismatch"):
        RealModelAdapter(model_dir=tmp_path, ml_package_dir=ML_DIR)


def test_agent_runs_end_to_end_on_the_real_model(adapter: RealModelAdapter) -> None:
    request = ForecastRequest(forecast_date=date(2026, 2, 1), horizon_hours=48, turbine_ids=[1, 2])
    response = asyncio.run(ForecastAgent(WeatherService(MockWeatherProvider()), adapter).run(request))

    assert response.status == "completed"
    statuses = {step.id: step.status for step in response.agent_steps}
    assert statuses.pop("recompute") in {"skipped", "completed"}
    assert set(statuses.values()) == {"completed"}
    assert response.model_version == ", ".join(sorted({_version(MODEL_DIR, 1), _version(MODEL_DIR, 2)}))
    assert all(len(turbine.points) == 48 for turbine in response.turbines)
    assert response.turbines[0].points[-1].timestamp == FEB_01 + timedelta(hours=47)
