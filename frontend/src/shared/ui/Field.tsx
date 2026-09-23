import type { ReactNode } from "react";

import { cn } from "@/shared/lib";

type FieldProps = {
  label: string;
  htmlFor?: string;
  labelId?: string;
  icon: ReactNode;
  className?: string;
  children: ReactNode;
};

/** Control-bar field: icon well on the left, small label above the control. */
export function Field({ label, htmlFor, labelId, icon, className, children }: FieldProps) {
  return (
    <div className={cn("field flex h-[62px] min-w-0 items-stretch rounded-[12px]", className)}>
      <span aria-hidden className="grid w-[54px] shrink-0 place-items-center border-r border-line text-cream/75">
        {icon}
      </span>
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-0.5 px-4">
        <label id={labelId} htmlFor={htmlFor} className="text-[12px] text-ink-muted">
          {label}
        </label>
        {children}
      </div>
    </div>
  );
}
