import { CircleCheck, CircleX, Loader } from "lucide-react";

import { formatDuration } from "@/shared/lib";
import { Badge } from "@/shared/ui";

export type AgentRunState = "idle" | "running" | "revealing" | "completed" | "failed";

type AgentRunBadgeProps = {
  state: AgentRunState;
  totalDurationMs: number;
};

export function AgentRunBadge({ state, totalDurationMs }: AgentRunBadgeProps) {
  switch (state) {
    case "idle":
      return <Badge>Idle</Badge>;
    case "running":
    case "revealing":
      return (
        <Badge tone="accent">
          <Loader className="size-3 animate-spin" aria-hidden />
          Running
        </Badge>
      );
    case "completed":
      return (
        <Badge tone="good">
          <CircleCheck className="size-3 text-status-good" aria-hidden />
          Completed · {formatDuration(totalDurationMs)}
        </Badge>
      );
    case "failed":
      return (
        <Badge tone="critical">
          <CircleX className="size-3 text-status-critical" aria-hidden />
          Failed
        </Badge>
      );
  }
}
