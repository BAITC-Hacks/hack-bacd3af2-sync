import { Check, Loader, SkipForward, X } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";

import type { AgentStepStatus } from "@/entities/agent";
import { cn } from "@/shared/lib";

const STATUS_STYLES: Record<AgentStepStatus, string> = {
  pending: "border-line text-transparent",
  running: "border-cream/60 text-cream",
  completed: "border-sage/60 bg-sage/[0.12] text-sage",
  failed: "border-status-critical/70 bg-status-critical/10 text-status-critical",
  skipped: "border-line-strong text-ink-subtle",
};

function Icon({ status }: { status: AgentStepStatus }) {
  const className = "size-3.5";
  switch (status) {
    case "completed":
      return <Check className={className} strokeWidth={2.4} />;
    case "failed":
      return <X className={className} strokeWidth={2.4} />;
    case "running":
      return <Loader className={cn(className, "animate-spin")} strokeWidth={2} />;
    case "skipped":
      return <SkipForward className="size-3" strokeWidth={2} />;
    case "pending":
      return <span className="size-1 rounded-full bg-ink-subtle" />;
  }
}

export function StepStatusIcon({ status }: { status: AgentStepStatus }) {
  return (
    <span
      aria-hidden
      className={cn(
        "relative z-10 grid size-[26px] shrink-0 place-items-center rounded-full border bg-canvas transition-colors duration-300",
        STATUS_STYLES[status],
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={status}
          className="grid place-items-center"
          initial={{ scale: 0.5, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.5, opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <Icon status={status} />
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
