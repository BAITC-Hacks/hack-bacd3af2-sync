import { useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";

import type { AgentStep } from "../types/agent";

const STEP_REVEAL_INTERVAL_MS = 320;

type StepReveal = {
  steps: AgentStep[];
  isRevealing: boolean;
};

/**
 * Plays back the backend's real step results one by one so the timeline reads as a sequence.
 * Only the transition is smoothed: each executed step briefly shows "running" before its
 * real status. Statuses, messages and durations are never invented.
 */
export function useStepReveal(steps: AgentStep[] | undefined, runKey: string | undefined): StepReveal {
  const shouldReduceMotion = useReducedMotion();
  const total = steps?.length ?? 0;
  const [revealed, setRevealed] = useState({ key: runKey, count: 0 });

  // Restart playback when a new run arrives (state adjustment during render, no effect needed).
  if (revealed.key !== runKey) {
    setRevealed({ key: runKey, count: shouldReduceMotion ? total : 0 });
  }
  const count = revealed.key === runKey ? revealed.count : 0;

  useEffect(() => {
    if (count >= total) return;
    const timer = window.setTimeout(
      () => setRevealed((current) => ({ ...current, count: current.count + 1 })),
      STEP_REVEAL_INTERVAL_MS,
    );
    return () => window.clearTimeout(timer);
  }, [count, total]);

  if (!steps) return { steps: [], isRevealing: false };

  const played = steps.map((step, index): AgentStep => {
    if (index < count) return step;
    const isCurrent = index === count && step.status !== "skipped";
    return { ...step, status: isCurrent ? "running" : "pending", durationMs: undefined };
  });

  return { steps: played, isRevealing: count < total };
}
