import { motion } from "motion/react";

import { AGENT_PIPELINE, type AgentStep } from "@/entities/agent";
import { baseTransition } from "@/shared/config";
import { cn, formatDuration } from "@/shared/lib";

import { StepStatusIcon } from "./StepStatusIcon";

const STATUS_LABELS: Record<AgentStep["status"], string> = {
  pending: "Pending",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  skipped: "Skipped",
};

type AgentStepItemProps = {
  step: AgentStep;
  index: number;
  isLast: boolean;
};

function describe(step: AgentStep): string {
  // Unexecuted steps show the plan; executed steps show the backend's real message.
  if (step.status === "pending" || step.status === "running") {
    return AGENT_PIPELINE.find((stage) => stage.id === step.id)?.description ?? "";
  }
  return step.message;
}

export function AgentStepItem({ step, index, isLast }: AgentStepItemProps) {
  const isDone = step.status === "completed";
  const isMuted = step.status === "pending" || step.status === "skipped";

  return (
    <motion.li
      className="relative flex gap-3.5 pb-5 last:pb-0"
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ ...baseTransition, delay: index * 0.05 }}
    >
      {!isLast ? (
        <span aria-hidden className="absolute top-8 bottom-1 left-[13px] w-px bg-line">
          <motion.span
            className="absolute inset-x-0 top-0 bg-gradient-to-b from-status-good/70 to-status-good/20"
            initial={false}
            animate={{ height: isDone ? "100%" : "0%" }}
            transition={{ duration: 0.3 }}
          />
        </span>
      ) : null}

      <StepStatusIcon status={step.status} />

      <div className="min-w-0 flex-1 pt-0.5">
        <div className="flex items-center justify-between gap-3">
          <p className={cn("text-sm font-medium", isMuted ? "text-ink-muted" : "text-ink")}>
            {step.title}
            <span className="sr-only"> — {STATUS_LABELS[step.status]}</span>
          </p>
          {step.durationMs !== undefined ? (
            <span className="shrink-0 rounded-md bg-white/[0.04] px-1.5 py-0.5 font-mono text-[11px] text-ink-muted tabular-nums">
              {formatDuration(step.durationMs)}
            </span>
          ) : null}
        </div>
        <p
          className={cn(
            "mt-0.5 text-[13px] leading-relaxed",
            step.status === "failed" ? "text-ink" : "text-ink-subtle",
          )}
        >
          {describe(step)}
        </p>
      </div>
    </motion.li>
  );
}
