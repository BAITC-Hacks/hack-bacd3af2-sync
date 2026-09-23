import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib";

type CardProps = HTMLAttributes<HTMLElement> & {
  /** Slightly stronger hairline for the card currently in focus (e.g. while the agent runs). */
  active?: boolean;
};

export function Card({ className, active = false, children, ...props }: CardProps) {
  return (
    <section
      className={cn(
        "panel rounded-[18px] p-5 transition-[border-color] duration-500",
        active && "border-line-strong",
        className,
      )}
      {...props}
    >
      {children}
    </section>
  );
}

type CardHeaderProps = {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
  titleId?: string;
};

export function CardHeader({ title, description, icon, action, className, titleId }: CardHeaderProps) {
  return (
    <header className={cn("mb-4 flex flex-wrap items-start justify-between gap-x-4 gap-y-3", className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? <span className="mt-1 shrink-0 text-cream/80">{icon}</span> : null}
        <div className="min-w-0">
          <h2 id={titleId} className="font-display text-[19px] leading-tight text-ink">
            {title}
          </h2>
          {description ? <p className="mt-0.5 text-[12.5px] text-ink-muted">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
