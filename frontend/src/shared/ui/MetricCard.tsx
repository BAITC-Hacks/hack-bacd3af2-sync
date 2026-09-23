import type { ReactNode } from "react";

import { cn } from "@/shared/lib";

import { Skeleton } from "./Skeleton";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  isLoading?: boolean;
  className?: string;
};

export function MetricCard({ label, value, hint, icon, isLoading = false, className }: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-line bg-white/[0.025] p-4 transition-colors hover:border-line-strong",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-2 text-xs font-medium text-ink-muted">
        <span>{label}</span>
        {icon ? <span className="text-ink-subtle">{icon}</span> : null}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-ink tabular-nums sm:text-[28px]">
        {isLoading ? <Skeleton className="h-8 w-20" /> : value}
      </div>
      {hint ? <div className="mt-1 text-xs text-ink-subtle">{isLoading ? " " : hint}</div> : null}
    </div>
  );
}
