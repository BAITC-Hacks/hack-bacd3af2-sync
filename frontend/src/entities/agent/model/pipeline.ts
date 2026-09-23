import type { AgentStep, AgentStepId } from "../types/agent";

type PipelineStage = {
  id: AgentStepId;
  title: string;
  description: string;
};

/**
 * The agent's plan, shown before a run has produced real step results.
 * Titles match the backend; statuses always come from the backend response.
 */
export const AGENT_PIPELINE: readonly PipelineStage[] = [
  { id: "fetch_weather", title: "Fetch weather forecast", description: "Hourly wind speed & temperature per turbine" },
  { id: "validate_weather", title: "Validate weather data", description: "Schema, continuity, physical ranges, gap repair" },
  { id: "prepare_features", title: "Prepare model inputs", description: "Contract-shaped frames for the ML model" },
  { id: "run_model", title: "Run ML model", description: "Hourly normalized power per turbine" },
  { id: "validate_prediction", title: "Validate prediction", description: "NaN, [0, 1] bounds, horizon, anomalies" },
  { id: "generate_explanation", title: "Generate explanation", description: "Narrative summary of the forecast" },
];

export function planAsPendingSteps(): AgentStep[] {
  return AGENT_PIPELINE.map((stage) => ({
    id: stage.id,
    title: stage.title,
    status: "pending",
    message: stage.description,
  }));
}
