import { Check, CircleDashed, Loader, SkipForward, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import type { AgentStepStatus } from "@/entities/agent";
import { cn } from "@/shared/lib";

const STATUS_STYLES: Record<AgentStepStatus, string> = {
  pending: "border-line text-ink-subtle bg-white/[0.02]",
  running: "border-cyan-400/50 text-accent bg-cyan-400/10 shadow-[0_0_18px_-4px_rgb(34_211_238/0.8)]",
  completed: "border-status-good/50 text-status-good bg-status-good/10",
  failed: "border-status-critical/60 text-status-critical bg-status-critical/10",
  skipped: "border-line text-ink-subtle bg-transparent",
};

function Icon({ status }: { status: AgentStepStatus }) {
  const className = "size-3.5";
  switch (status) {
    case "completed":
      return <Check className={className} strokeWidth={3} />;
    case "failed":
      return <X className={className} strokeWidth={3} />;
    case "running":
      return <Loader className={cn(className, "animate-spin")} />;
    case "skipped":
      return <SkipForward className={className} />;
    case "pending":
      return <CircleDashed className={className} />;
  }
}

export function StepStatusIcon({ status }: { status: AgentStepStatus }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative z-10 grid size-7 shrink-0 place-items-center rounded-full border transition-[background-color,border-color,box-shadow] duration-300",
        STATUS_STYLES[status],
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={status}
          initial={{ scale: 0.4, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.4, opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <Icon status={status} />
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
