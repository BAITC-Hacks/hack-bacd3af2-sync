"""Closed agentic loop: analyze_result → (at most one) recompute → LLM or template explanation."""

import asyncio
from datetime import date, datetime
from types import SimpleNamespace

import httpx2
import numpy as np
import openai
import pandas as pd
import pytest

from app.agent.forecast_agent import ForecastAgent
from app.core.config import Settings
from app.core.constants import Turbine
from app.ml.mock_model import MockModelAdapter
from app.ml.model_adapter import ModelAdapter
from app.schemas.forecast import ForecastRequest, ForecastResponse
from app.services.llm_explainer import LlmExplainerError, OpenAIExplainer
from app.services.weather_service import (
    MockWeatherProvider,
    WeatherProvider,
    WeatherProviderError,
    WeatherService,
)

REQUEST = ForecastRequest(forecast_date=date(2026, 2, 10), horizon_hours=24, turbine_ids=[1, 2])
TURBINE_COUNT = len(REQUEST.turbine_ids)


def _run(agent: ForecastAgent) -> ForecastResponse:
    return asyncio.run(agent.run(REQUEST))


def _step(response: ForecastResponse, step_id: str):  # noqa: ANN202 — AgentStep
    return next(step for step in response.agent_steps if step.id == step_id)


# --- fakes ------------------------------------------------------------------------------


class _CountingModel(ModelAdapter):
    """Mock model that can corrupt its first `bad_calls` predictions and counts every call."""

    name = "Counting"

    def __init__(self, bad_calls: int = 0, mode: str = "out_of_bounds", crash_after: int | None = None) -> None:
        self._inner = MockModelAdapter()
        self._bad_calls = bad_calls
        self._mode = mode
        self._crash_after = crash_after
        self.calls = 0

    async def predict(
        self, turbine_id: int, weather: pd.DataFrame, horizon_hours: int, forecast_origin: datetime
    ) -> pd.DataFrame:
        self.calls += 1
        if self._crash_after is not None and self.calls > self._crash_after:
            raise RuntimeError("model file is corrupted")
        frame = await self._inner.predict(turbine_id, weather, horizon_hours, forecast_origin)
        if self.calls <= self._bad_calls:
            if self._mode == "out_of_bounds":
                frame.loc[0, "predicted_power"] = 1.4
                frame.loc[1, "predicted_power"] = -0.2
            elif self._mode == "constant":
                frame["predicted_power"] = 0.5
        return frame


class _FlakyPrimary(WeatherProvider):
    """Fails the first `failures` calls, then serves (mock) data as the live provider."""

    source = "open_meteo"

    def __init__(self, failures: int) -> None:
        self._failures_left = failures
        self.calls = 0

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        self.calls += 1
        if self._failures_left > 0:
            self._failures_left -= 1
            raise WeatherProviderError("connection refused")
        return await MockWeatherProvider().fetch_hourly(turbine, start, hours)


class _CalmWeather(WeatherProvider):
    source = "mock"

    async def fetch_hourly(self, turbine: Turbine, start: datetime, hours: int) -> pd.DataFrame:
        frame = await MockWeatherProvider().fetch_hourly(turbine, start, hours)
        frame["wind_speed"] = 1.0  # below cut-in: any real output is physically inconsistent
        return frame


class _FakeExplainer:
    name = "FakeLLM"

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.facts: dict[str, object] | None = None

    async def explain(self, facts: dict[str, object]) -> str:
        self.facts = facts
        if self._error is not None:
            raise self._error
        return "LLM: steady generation expected."


def _mock_weather() -> WeatherService:
    return WeatherService(MockWeatherProvider())


# --- analyze_result / recompute ---------------------------------------------------------


def test_clean_input_needs_no_recompute() -> None:
    model = _CountingModel()
    response = _run(ForecastAgent(_mock_weather(), model))

    assert response.status == "completed"
    assert _step(response, "analyze_result").status == "completed"
    assert "No recompute needed" in _step(response, "analyze_result").message
    recompute = _step(response, "recompute")
    assert recompute.status == "skipped" and "Not needed" in recompute.message
    assert model.calls == TURBINE_COUNT  # the model ran exactly once per turbine
    assert "no reason to recompute" in response.explanation


def test_clipped_values_trigger_one_recompute_that_resolves_them() -> None:
    model = _CountingModel(bad_calls=TURBINE_COUNT)  # only the first pass is corrupted
    response = _run(ForecastAgent(_mock_weather(), model))

    assert response.status == "completed"
    assert "Clipped 4" in _step(response, "validate_prediction").message
    assert "clipped" in _step(response, "analyze_result").message
    recompute = _step(response, "recompute")
    assert recompute.status == "completed" and "All triggers resolved" in recompute.message
    assert recompute.duration_ms is not None
    assert model.calls == 2 * TURBINE_COUNT
    # The adopted result is the clean one: no clipping warning left, explanation says why it recomputed.
    assert not any("clipped" in warning for warning in response.warnings)
    assert "recomputed the forecast once because" in response.explanation


def test_persistent_trigger_recomputes_at_most_once_and_warns() -> None:
    model = _CountingModel(bad_calls=10_000)  # every call is corrupted
    response = _run(ForecastAgent(_mock_weather(), model))

    assert response.status == "completed"
    assert [step.id for step in response.agent_steps].count("recompute") == 1
    assert model.calls == 2 * TURBINE_COUNT  # first pass + exactly one recompute, no loop
    assert "Trigger persists" in _step(response, "recompute").message
    assert any("treat this forecast with caution" in warning for warning in response.warnings)


def test_fallback_weather_is_replaced_when_primary_recovers() -> None:
    primary = _FlakyPrimary(failures=TURBINE_COUNT)  # down for the first fetch only
    weather = WeatherService(primary, fallback=MockWeatherProvider())
    response = _run(ForecastAgent(weather, _CountingModel()))

    assert response.status == "completed"
    assert "answered on retry" in _step(response, "analyze_result").message
    assert _step(response, "recompute").status == "completed"
    assert response.weather_source == "open_meteo"
    assert not any("unavailable" in warning for warning in response.warnings)


def test_fallback_weather_is_kept_when_primary_is_still_down() -> None:
    primary = _FlakyPrimary(failures=10_000)
    weather = WeatherService(primary, fallback=MockWeatherProvider())
    response = _run(ForecastAgent(weather, _CountingModel()))

    assert response.status == "completed"
    assert "still unavailable" in _step(response, "analyze_result").message
    assert _step(response, "recompute").status == "skipped"
    assert response.weather_source == "mock"
    assert any("unavailable" in warning for warning in response.warnings)


def test_physically_inconsistent_hours_trigger_recompute() -> None:
    model = _CountingModel(bad_calls=10_000, mode="constant")  # 50% output while wind is 1 m/s
    response = _run(ForecastAgent(WeatherService(_CalmWeather()), model))

    analyze = _step(response, "analyze_result")
    assert "contradict the wind" in analyze.message and "calm but producing" in analyze.message
    assert _step(response, "recompute").status == "completed"
    assert "physically inconsistent" in _step(response, "recompute").message


def test_failed_recompute_keeps_the_original_forecast() -> None:
    model = _CountingModel(bad_calls=TURBINE_COUNT, crash_after=TURBINE_COUNT)
    response = _run(ForecastAgent(_mock_weather(), model))

    recompute = _step(response, "recompute")
    assert recompute.status == "failed" and "kept the original validated forecast" in recompute.message
    assert response.status == "completed"  # recompute is non-fatal
    assert response.summary is not None and len(response.turbines) == TURBINE_COUNT
    assert _step(response, "generate_explanation").status == "completed"
    assert "the recompute failed" in response.explanation


# --- generate_explanation: LLM and fallback ---------------------------------------------


def test_llm_explanation_receives_real_numbers_and_recompute_decision() -> None:
    explainer = _FakeExplainer()
    response = _run(ForecastAgent(_mock_weather(), _CountingModel(bad_calls=TURBINE_COUNT), explainer))

    assert response.explanation == "LLM: steady generation expected."
    assert response.explanation_source == "llm"
    assert "FakeLLM explained" in _step(response, "generate_explanation").message
    facts = explainer.facts
    assert facts is not None
    assert facts["fleet_average_power"] == pytest.approx(response.summary.average_power, abs=1e-3)  # type: ignore[union-attr]
    assert facts["recompute"] == {
        "performed": True,
        "reasons": ["4 predicted value(s) fell outside [0, 1] and had to be clipped"],
        "outcome": "the recomputed forecast passed all checks and replaced the first result.",
    }
    assert len(facts["peak_hours"]) == 3  # type: ignore[arg-type]


@pytest.mark.parametrize("error", [LlmExplainerError("LLM unreachable: APIConnectionError"), ValueError("boom")])
def test_llm_failure_falls_back_to_template(error: Exception) -> None:
    response = _run(ForecastAgent(_mock_weather(), _CountingModel(), _FakeExplainer(error)))

    assert response.status == "completed"
    assert response.explanation_source == "template"
    assert response.explanation.startswith("Over the next 24 hours")
    step = _step(response, "generate_explanation")
    assert step.status == "completed" and "used the template explanation" in step.message


def test_no_api_key_uses_template_without_calling_llm() -> None:
    response = _run(ForecastAgent(_mock_weather(), _CountingModel(), explainer=None))

    assert response.explanation_source == "template"
    assert "OPENAI_API_KEY is not set" in _step(response, "generate_explanation").message


def test_blank_api_key_disables_llm() -> None:
    assert Settings(openai_api_key="   ").llm_enabled is False
    assert Settings(openai_api_key="").llm_enabled is False
    assert Settings(openai_api_key="placeholder-not-a-real-key").llm_enabled is True


def test_openai_defaults() -> None:
    settings = Settings()
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.openai_timeout_s == 10.0


# --- OpenAIExplainer against a fake SDK client (no network) ------------------------------


def _fake_client(result: object) -> tuple[SimpleNamespace, SimpleNamespace]:
    """Mimics the synchronous OpenAI client surface: client.chat.completions.create(**kwargs)."""
    calls = SimpleNamespace(kwargs={})

    def create(**kwargs: object) -> object:
        calls.kwargs = kwargs
        if isinstance(result, Exception):
            raise result
        return result

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))), calls


def _completion(finish_reason: str, content: str | None, refusal: str | None = None) -> SimpleNamespace:
    message = SimpleNamespace(content=content, refusal=refusal)
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish_reason, message=message)],
        model="gpt-4o-mini",
        _request_id="req_test",
    )


def _explainer(result: object) -> tuple[OpenAIExplainer, SimpleNamespace]:
    client, calls = _fake_client(result)
    explainer = OpenAIExplainer(model="gpt-4o-mini", timeout_s=10, client=client)  # type: ignore[arg-type]
    return explainer, calls


def test_openai_explainer_returns_text_and_sends_facts_with_timeout() -> None:
    explainer, calls = _explainer(_completion("stop", "  Moderate generation.  "))
    text = asyncio.run(explainer.explain({"fleet_average_power": 0.57}))

    assert text == "Moderate generation."
    assert explainer.name == "OpenAI (gpt-4o-mini)"
    assert calls.kwargs["model"] == "gpt-4o-mini"
    assert calls.kwargs["timeout"] == 10
    system, user = calls.kwargs["messages"]
    assert system["role"] == "system" and "recomputed" in system["content"]
    assert user["role"] == "user" and '"fleet_average_power": 0.57' in user["content"]


def test_openai_explainer_accepts_a_real_sdk_completion_object() -> None:
    """Parse a genuine ChatCompletion (no fake attributes) — guards against SDK attribute drift."""
    from openai.types.chat import ChatCompletion

    completion = ChatCompletion.model_validate(
        {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": "Steady output.", "refusal": None},
                }
            ],
        }
    )
    explainer, _ = _explainer(completion)
    assert asyncio.run(explainer.explain({})) == "Steady output."


_REQUEST = httpx2.Request("POST", "https://api.openai.com/v1/chat/completions")


@pytest.mark.parametrize(
    "result",
    [
        _completion("stop", None, refusal="I can't help with that."),
        _completion("content_filter", ""),
        _completion("length", "Cut off"),
        _completion("stop", "   "),
        SimpleNamespace(choices=[], model="gpt-4o-mini", _request_id=None),
        openai.APIConnectionError(request=_REQUEST),
        openai.APITimeoutError(request=_REQUEST),
        openai.AuthenticationError("bad key", response=httpx2.Response(401, request=_REQUEST), body=None),
        openai.RateLimitError("quota", response=httpx2.Response(429, request=_REQUEST), body=None),
    ],
)
def test_openai_explainer_maps_every_failure_to_explainer_error(result: object) -> None:
    explainer, _ = _explainer(result)
    with pytest.raises(LlmExplainerError):
        asyncio.run(explainer.explain({}))


def test_consistency_check_counts_calm_and_windy_contradictions() -> None:
    from app.services.analysis_service import check_physical_consistency

    frame = pd.DataFrame(
        {
            "wind_speed": np.array([1.0, 1.0, 12.0, 12.0, 8.0]),
            "predicted_power": np.array([0.5, 0.0, 0.01, 0.9, 0.4]),
        }
    )
    check = check_physical_consistency({1: frame})
    assert (check.calm_but_producing, check.windy_but_idle, check.total_hours) == (1, 1, 5)
    assert check.share == pytest.approx(0.4)
