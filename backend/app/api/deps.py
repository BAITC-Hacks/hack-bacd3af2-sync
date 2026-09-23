"""Dependency wiring. The only place that decides which implementations are used."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.agent.forecast_agent import ForecastAgent
from app.core.config import get_settings
from app.ml.mock_model import MockModelAdapter
from app.ml.model_adapter import ModelAdapter
from app.ml.real_model import RealModelAdapter
from app.services.forecast_service import ForecastService
from app.services.metrics_service import MetricsService
from app.services.weather_service import (
    MockWeatherProvider,
    OpenMeteoWeatherProvider,
    WeatherService,
)


@lru_cache
def get_model_adapter() -> ModelAdapter:
    # TODO: Replace MockModelAdapter with RealModelAdapter after ML model is ready
    #       (set MODEL_ADAPTER=real in backend/.env).
    if get_settings().model_adapter == "real":
        return RealModelAdapter()
    return MockModelAdapter()


@lru_cache
def get_weather_service() -> WeatherService:
    settings = get_settings()
    if settings.weather_provider == "open_meteo":
        live = OpenMeteoWeatherProvider(settings.open_meteo_url, settings.open_meteo_timeout_s)
        return WeatherService(provider=live, fallback=MockWeatherProvider())
    return WeatherService(provider=MockWeatherProvider())


@lru_cache
def get_forecast_service() -> ForecastService:
    agent = ForecastAgent(weather_service=get_weather_service(), model_adapter=get_model_adapter())
    return ForecastService(agent)


@lru_cache
def get_metrics_service() -> MetricsService:
    return MetricsService(get_settings().metrics_file)


ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
MetricsServiceDep = Annotated[MetricsService, Depends(get_metrics_service)]
