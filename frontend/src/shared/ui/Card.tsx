import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/shared/lib";

type CardProps = HTMLAttributes<HTMLElement> & {
  /** Adds the cyan/violet halo — used for the active forecast card. */
  glow?: boolean;
};

export function Card({ className, glow = false, children, ...props }: CardProps) {
  return (
    <section className={cn("glass rounded-2xl p-5 sm:p-6", glow && "glow-ring", className)} {...props}>
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
    <header className={cn("mb-5 flex flex-wrap items-start justify-between gap-x-4 gap-y-3", className)}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <span className="grid size-9 shrink-0 place-items-center rounded-xl border border-line bg-white/[0.04] text-accent">
            {icon}
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 id={titleId} className="text-[15px] font-semibold tracking-tight text-ink">
            {title}
          </h2>
          {description ? <p className="mt-0.5 text-sm text-ink-muted">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}
