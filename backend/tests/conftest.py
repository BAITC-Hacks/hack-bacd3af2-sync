"""Tests are hermetic: no real LLM calls, deterministic weather and model, regardless of backend/.env."""

import os

# Environment variables take precedence over backend/.env in pydantic-settings.
os.environ["OPENAI_API_KEY"] = ""
os.environ["WEATHER_PROVIDER"] = "mock"
os.environ["MODEL_ADAPTER"] = "mock"
