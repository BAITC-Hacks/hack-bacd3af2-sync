export type AgentStepId =
  | "fetch_weather"
  | "validate_weather"
  | "prepare_features"
  | "run_model"
  | "validate_prediction"
  | "analyze_result"
  | "recompute"
  | "generate_explanation";

/** "skipped" = not executed: an earlier step failed, or (recompute) the analysis found no need. */
export type AgentStepStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export type AgentStep = {
  id: AgentStepId;
  title: string;
  status: AgentStepStatus;
  message: string;
  durationMs?: number;
};
