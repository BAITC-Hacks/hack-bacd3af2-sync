export type AgentStepId =
  | "fetch_weather"
  | "validate_weather"
  | "prepare_features"
  | "run_model"
  | "validate_prediction"
  | "generate_explanation";

/** "skipped" = never executed because an earlier step failed. */
export type AgentStepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export type AgentStep = {
  id: AgentStepId;
  title: string;
  status: AgentStepStatus;
  message: string;
  durationMs?: number;
};
