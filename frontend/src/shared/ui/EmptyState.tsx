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
        "flex h-full flex-col items-center justify-center rounded-[14px] border border-dashed border-line px-6 py-10 text-center",
        className,
      )}
    >
      <span className="text-ink-subtle">{icon}</span>
      <p className="mt-3 font-display text-lg text-ink">{title}</p>
      <p className="mt-1 max-w-sm text-[13px] text-ink-muted">{description}</p>
    </div>
  );
}
