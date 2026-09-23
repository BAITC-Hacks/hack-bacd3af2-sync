import type { ReactNode } from "react";

import { cn } from "@/shared/lib";

type EmptyStateProps = {
  icon: ReactNode;
  title: string;
  description: string;
  className?: string;
};

export function EmptyState({ icon, title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex h-full flex-col items-center justify-center rounded-xl border border-dashed border-line px-6 py-10 text-center",
        className,
      )}
    >
      <span className="grid size-11 place-items-center rounded-2xl border border-line bg-white/[0.03] text-ink-subtle">
        {icon}
      </span>
      <p className="mt-3 text-sm font-medium text-ink">{title}</p>
      <p className="mt-1 max-w-sm text-sm text-ink-muted">{description}</p>
    </div>
  );
}
