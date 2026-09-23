"""Agent step primitives: the pipeline plan, the shared run context and a timed step executor."""

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Final

import pandas as pd

from app.schemas.agent import AgentStep, AgentStepId
from app.schemas.forecast import ForecastRequest, ForecastSummary

logger = logging.getLogger(__name__)

PIPELINE: Final[tuple[AgentStepId, ...]] = (
    "fetch_weather",
    "validate_weather",
    "prepare_features",
    "run_model",
    "validate_prediction",
    "generate_explanation",
)

STEP_TITLES: Final[dict[AgentStepId, str]] = {
    "fetch_weather": "Fetch weather forecast",
    "validate_weather": "Validate weather data",
    "prepare_features": "Prepare model inputs",
    "run_model": "Run ML model",
    "validate_prediction": "Validate prediction",
    "generate_explanation": "Generate explanation",
}


class StepFailedError(Exception):
    """Raised by a step handler when the pipeline cannot continue."""


@dataclass(slots=True)
class AgentContext:
    """Mutable state shared by all steps of a single agent run."""

    request: ForecastRequest
    forecast_origin: datetime
    weather: dict[int, pd.DataFrame] = field(default_factory=dict)
    weather_source: str | None = None
    model_inputs: dict[int, pd.DataFrame] = field(default_factory=dict)
    predictions: dict[int, pd.DataFrame] = field(default_factory=dict)
    model_version: str | None = None
    summary: ForecastSummary | None = None
    explanation: str = ""
    warnings: list[str] = field(default_factory=list)


StepHandler = Callable[[AgentContext], Awaitable[str]]


async def execute_step(step_id: AgentStepId, handler: StepHandler, context: AgentContext) -> AgentStep:
    """Run one step, measuring wall-clock time. The handler returns the step message."""
    started = time.perf_counter()
    try:
        message = await handler(context)
        status = "completed"
    except StepFailedError as exc:
        message, status = str(exc), "failed"
    except Exception as exc:  # noqa: BLE001 — any crash must surface as a failed step, not a 500
        logger.exception("Agent step %s crashed", step_id)
        message, status = f"Unexpected error: {exc}", "failed"
    duration_ms = round((time.perf_counter() - started) * 1000)
    return AgentStep(
        id=step_id,
        title=STEP_TITLES[step_id],
        status=status,
        message=message,
        duration_ms=duration_ms,
    )


def skipped_step(step_id: AgentStepId, failed_step: AgentStepId) -> AgentStep:
    return AgentStep(
        id=step_id,
        title=STEP_TITLES[step_id],
        status="skipped",
        message=f"Not executed because “{STEP_TITLES[failed_step]}” failed.",
    )
