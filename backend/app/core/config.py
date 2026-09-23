from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings, loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    app_name: str = "WindAI"
    env: Literal["development", "production", "test"] = "development"
    api_prefix: str = "/api"

    # Comma-separated list, e.g. "http://localhost:5173,http://127.0.0.1:5173".
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # "mock" works out of the box; "real" requires app/ml/predictor.py and models/*.cbm.
    model_adapter: Literal["mock", "real"] = "mock"
    models_dir: Path = BACKEND_ROOT / "models"
    metrics_file: Path = BACKEND_ROOT / "models" / "metrics.json"

    # "mock" is deterministic and offline; "open_meteo" calls the Historical Forecast API
    # and falls back to mock weather if the API is unreachable.
    weather_provider: Literal["mock", "open_meteo"] = "mock"
    open_meteo_url: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    open_meteo_timeout_s: float = Field(default=10.0, gt=0)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
