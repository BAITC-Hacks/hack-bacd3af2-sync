import { cn } from "@/shared/lib";

import { useApiHealth } from "../model/useApiHealth";

const STATES = {
  online: { label: "API online", dot: "bg-status-good" },
  offline: { label: "API offline", dot: "bg-status-critical" },
  checking: { label: "Connecting…", dot: "bg-ink-subtle animate-pulse-soft" },
} as const;

export function ApiStatus() {
  const { isSuccess, isError } = useApiHealth();
  const state = isSuccess ? STATES.online : isError ? STATES.offline : STATES.checking;

  return (
    <span
      role="status"
      className="inline-flex items-center gap-2 rounded-full border border-line bg-white/[0.03] px-3 py-1 text-xs text-ink-muted"
    >
      <span className="relative flex size-2">
        {isSuccess ? <span className="absolute inset-0 animate-ping rounded-full bg-status-good/60" /> : null}
        <span className={cn("relative size-2 rounded-full", state.dot)} />
      </span>
      {state.label}
    </span>
  );
}
