from typing import Literal

from pydantic import BaseModel, Field

AgentStepId = Literal[
    "fetch_weather",
    "validate_weather",
    "prepare_features",
    "run_model",
    "validate_prediction",
    "generate_explanation",
]

# "skipped" marks steps that never ran because an earlier step failed.
AgentStepStatus = Literal["pending", "running", "completed", "failed", "skipped"]


class AgentStep(BaseModel):
    id: AgentStepId
    title: str
    status: AgentStepStatus
    message: str
    duration_ms: int | None = Field(default=None, ge=0)
