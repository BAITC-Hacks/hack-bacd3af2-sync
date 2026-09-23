"""Dependency wiring. The only place that decides which implementations are used."""

import os
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.agent.forecast_agent import ForecastAgent
from app.core.config import get_settings
from app.ml.mock_model import MockModelAdapter
from app.ml.model_adapter import ModelAdapter
from app.ml.real_model import RealModelAdapter
from app.services.forecast_service import ForecastService
from app.services.llm_explainer import ForecastExplainer, OpenAIExplainer
from app.services.metrics_service import MetricsService
from app.services.weather_service import (
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
    WeatherService,
)


@lru_cache
def get_model_adapter() -> ModelAdapter:
    # MODEL_ADAPTER=real → the ML team's CatBoost models (fails fast if they cannot load);
    # MODEL_ADAPTER=mock → offline power-curve stand-in with the same output contract.
    settings = get_settings()
    if settings.model_adapter == "real":
        return RealModelAdapter(model_dir=settings.turbine_model_dir, ml_package_dir=settings.ml_package_dir)
    return MockModelAdapter()


@lru_cache
def get_weather_service() -> WeatherService:
    settings = get_settings()
    if settings.weather_provider == "open_meteo":
        live = OpenMeteoWeatherProvider(settings.open_meteo_url, settings.open_meteo_timeout_s)
        return WeatherService(provider=live, fallback=MockWeatherProvider())
    return WeatherService(provider=MockWeatherProvider())


@lru_cache
def get_explainer() -> ForecastExplainer | None:
    """OpenAI-written explanations when OPENAI_API_KEY is set; otherwise the agent uses its template."""
    settings = get_settings()
    if not settings.llm_enabled or settings.openai_api_key is None:
        return None
    # The SDK reads the key from the process environment. A key placed only in backend/.env is
    # loaded by pydantic-settings, not exported, so make it visible to the SDK (never overrides).
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key.strip())
    return OpenAIExplainer(
        model=settings.openai_model,
        timeout_s=settings.openai_timeout_s,
        language=settings.explanation_language,
    )


@lru_cache
def get_forecast_service() -> ForecastService:
    agent = ForecastAgent(
        weather_service=get_weather_service(),
        model_adapter=get_model_adapter(),
        explainer=get_explainer(),
        explanation_language=get_settings().explanation_language,
    )
    return ForecastService(agent)


@lru_cache
def get_metrics_service() -> MetricsService:
    # Real hold-out scores only describe the CatBoost models, so show them only when those serve.
    settings = get_settings()
    return MetricsService(settings.turbine_model_dir if settings.model_adapter == "real" else None)


ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
