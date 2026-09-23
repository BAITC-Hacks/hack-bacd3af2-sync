import type { ReactNode } from "react";

import { cn } from "@/shared/lib";

type FieldProps = {
  label: string;
  htmlFor?: string;
  labelId?: string;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
};

/** Label + control stack used in the forecast control bar. */
export function Field({ label, htmlFor, labelId, icon, className, children }: FieldProps) {
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <label
        id={labelId}
        htmlFor={htmlFor}
        className="flex items-center gap-1.5 text-[11px] font-medium tracking-[0.08em] text-ink-subtle uppercase"
      >
        {icon}
        {label}
      </label>
      {children}
    </div>
  );
}
