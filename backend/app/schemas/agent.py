from typing import Literal

from pydantic import BaseModel, Field

AgentStepId = Literal[
    "fetch_weather",
    "validate_weather",
    "prepare_features",
    "run_model",
    "validate_prediction",
    "analyze_result",
    "recompute",
    "generate_explanation",
]

# "skipped" marks steps that did not run: an earlier step failed, or (for "recompute")
# the analysis found no reason to run it. The step message states which.
AgentStepStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class AgentStep(BaseModel):
    id: AgentStepId
    title: str
    status: AgentStepStatus
    message: str
    duration_ms: int | None = Field(default=None, ge=0)
