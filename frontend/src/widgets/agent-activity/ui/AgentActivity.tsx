import { BrainCircuit, TriangleAlert } from "lucide-react";
import { useMemo } from "react";

import { planAsPendingSteps, useStepReveal } from "@/entities/agent";
import type { ForecastResponse } from "@/entities/forecast";
import type { ApiError } from "@/shared/api";
import { Card, CardHeader } from "@/shared/ui";

import { AgentRunBadge, type AgentRunState } from "./AgentRunBadge";
import { AgentStepItem } from "./AgentStepItem";

type AgentActivityProps = {
  forecast: ForecastResponse | undefined;
  isRunning: boolean;
  error: ApiError | null;
};

const PLAN = planAsPendingSteps();

function resolveRunState(forecast: ForecastResponse | undefined, isRunning: boolean, isRevealing: boolean): AgentRunState {
  if (isRunning) return "running";
  if (!forecast) return "idle";
  if (isRevealing) return "revealing";
  return forecast.status;
}

export function AgentActivity({ forecast, isRunning, error }: AgentActivityProps) {
  const reveal = useStepReveal(forecast?.agentSteps, forecast?.generatedAt);
  const runState = resolveRunState(forecast, isRunning, reveal.isRevealing);
  const steps = isRunning || !forecast ? PLAN : reveal.steps;
  const totalDurationMs = useMemo(
    () => forecast?.agentSteps.reduce((sum, step) => sum + (step.durationMs ?? 0), 0) ?? 0,
    [forecast],
  );

  return (
    <Card className="h-full" aria-labelledby="agent-title" glow={runState === "running" || runState === "revealing"}>
      <CardHeader
        titleId="agent-title"
        title="Agent status"
        description="Forecasting pipeline, executed step by step"
        icon={<BrainCircuit className="size-4" aria-hidden />}
        action={<AgentRunBadge state={runState} totalDurationMs={totalDurationMs} />}
      />

      <div className="relative">
        {isRunning ? (
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden rounded-xl">
            <div className="absolute inset-x-0 h-1/3 animate-scan bg-gradient-to-b from-transparent via-cyan-400/[0.06] to-transparent" />
          </div>
        ) : null}
        <ol aria-live="polite" aria-busy={isRunning || reveal.isRevealing}>
          {steps.map((step, index) => (
            <AgentStepItem key={step.id} step={step} index={index} isLast={index === steps.length - 1} />
          ))}
        </ol>
      </div>

      {isRunning ? (
        <p className="mt-4 text-xs text-ink-subtle">The agent is executing the pipeline on the backend…</p>
      ) : null}

      {error ? (
        <div role="alert" className="mt-4 flex gap-2.5 rounded-xl border border-status-critical/40 bg-status-critical/10 p-3 text-sm text-ink">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-status-critical" aria-hidden />
          <span>{error.message}</span>
        </div>
      ) : null}
    </Card>
  );
}
