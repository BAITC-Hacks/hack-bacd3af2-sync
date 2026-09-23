from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


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

    # "mock" works out of the box; "real" runs the ML team's CatBoost models via app/ml/predictor.py.
    model_adapter: Literal["mock", "real"] = "mock"
    models_dir: Path = BACKEND_ROOT / "models"
    # ML package root (holds src/); added to sys.path by the real adapter.
    ml_package_dir: Path = REPO_ROOT / "ml"
    # Main model bundles (turbine_N/). Earlier-cutoff snapshots live in asof_*/ subdirectories.
    turbine_model_dir: Path = REPO_ROOT / "ml" / "models"

    # "mock" is deterministic and offline; "open_meteo" calls the Historical Forecast API
    # and falls back to mock weather if the API is unreachable.
    weather_provider: Literal["mock", "open_meteo"] = "mock"
    open_meteo_url: str = "https://historical-forecast-api.open-meteo.com/v1/forecast"
    open_meteo_timeout_s: float = Field(default=10.0, gt=0)

    # LLM explanation step (OpenAI). Empty key → deterministic template explanation, no network call.
    # The OpenAI SDK reads OPENAI_API_KEY itself; the setting is only used to decide whether the LLM is on.
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_s: float = Field(default=10.0, gt=0)
    # The dashboard is in Russian, so LLM explanations default to Russian.
    explanation_language: Literal["en", "ru"] = "ru"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
