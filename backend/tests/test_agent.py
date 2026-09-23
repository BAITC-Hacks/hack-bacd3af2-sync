"""The agent must react to what services actually return — not report a fixed script."""

import asyncio
from datetime import date, datetime

import numpy as np
import pandas as pd

from app.agent.forecast_agent import ForecastAgent
from app.ml.mock_model import MockModelAdapter
from app.ml.model_adapter import ModelAdapter
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.weather_service import (
    MockWeatherProvider,
    WeatherProvider,
    WeatherProviderError,
    WeatherService,
)
from app.core.constants import Turbine

REQUEST = ForecastRequest(forecast_date=date(2026, 2, 10), horizon_hours=24, turbine_ids=[1, 2])


def _run(agent: ForecastAgent) -> ForecastResponse:
    return asyncio.run(agent.run(REQUEST))


def _statuses(response: ForecastResponse) -> dict[str, str]:
    return {step.id: step.status for step in response.agent_steps}


class _TamperingModel(ModelAdapter):
    """Wraps the mock model and corrupts its output."""

    name = "Tampering"

    def __init__(self, tamper: str) -> None:
        self._inner = MockModelAdapter()
        self._tamper = tamper

    async def predict(
        self, turbine_id: int, weather: pd.DataFrame, horizon_hours: int, forecast_origin: datetime
    ) -> pd.DataFrame:
        frame = await self._inner.predict(turbine_id, weather, horizon_hours, forecast_origin)
        if self._tamper == "out_of_bounds":
            frame.loc[0, "predicted_power"] = 1.4
            frame.loc[1, "predicted_power"] = -0.2
        elif self._tamper == "nan":
            frame.loc[3, "predicted_power"] = np.nan
        elif self._tamper == "crash":
            raise RuntimeError("model file is corrupted")
        return frame


class _GappyWeather(WeatherProvider):
    source = "mock"

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        frame = await MockWeatherProvider().fetch_hourly(turbine, start, hours)
        frame.loc[[4, 5], "wind_speed"] = np.nan
        return frame


class _DownProvider(WeatherProvider):
    source = "open_meteo"

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        raise WeatherProviderError("connection refused")


def test_out_of_bounds_predictions_are_clipped_with_warning() -> None:
    agent = ForecastAgent(WeatherService(MockWeatherProvider()), _TamperingModel("out_of_bounds"))
    response = _run(agent)

    assert response.status == "completed"
    powers = [p.predicted_power for t in response.turbines for p in t.points]
    assert min(powers) >= 0.0 and max(powers) <= 1.0
    assert any("clipped" in warning for warning in response.warnings)
    assert "Clipped 4" in response.agent_steps[4].message


def test_nan_predictions_fail_pipeline_and_skip_rest() -> None:
    agent = ForecastAgent(WeatherService(MockWeatherProvider()), _TamperingModel("nan"))
    response = _run(agent)

    assert response.status == "failed"
    assert response.summary is None
    assert _statuses(response)["validate_prediction"] == "failed"
    assert _statuses(response)["generate_explanation"] == "skipped"


def test_model_crash_is_reported_as_failed_step() -> None:
    agent = ForecastAgent(WeatherService(MockWeatherProvider()), _TamperingModel("crash"))
    response = _run(agent)

    assert response.status == "failed"
    assert _statuses(response)["run_model"] == "failed"
    assert "model file is corrupted" in response.explanation


def test_weather_gaps_are_interpolated() -> None:
    agent = ForecastAgent(WeatherService(_GappyWeather()), MockModelAdapter())
    response = _run(agent)

    assert response.status == "completed"
    assert "Interpolated 4 missing value(s)" in response.agent_steps[1].message


def test_weather_fallback_is_used_when_provider_is_down() -> None:
    agent = ForecastAgent(WeatherService(_DownProvider(), fallback=MockWeatherProvider()), MockModelAdapter())
    response = _run(agent)

    assert response.status == "completed"
    assert response.weather_source == "mock"
    assert any("unavailable" in warning for warning in response.warnings)


def test_weather_failure_without_fallback_fails_first_step() -> None:
    agent = ForecastAgent(WeatherService(_DownProvider()), MockModelAdapter())
    response = _run(agent)

    assert response.status == "failed"
    assert _statuses(response)["fetch_weather"] == "failed"
    assert list(_statuses(response).values())[1:] == ["skipped"] * 7
