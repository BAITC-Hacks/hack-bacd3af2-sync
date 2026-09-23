import { ChevronDown } from "lucide-react";
import type { SelectHTMLAttributes } from "react";

import { cn } from "@/shared/lib";

import { controlBase } from "./controlStyles";

export type SelectOption<TValue extends string> = {
  value: TValue;
  label: string;
};

type SelectProps<TValue extends string> = Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange"> & {
  value: TValue;
  options: readonly SelectOption<TValue>[];
  onValueChange: (value: TValue) => void;
};

export function Select<TValue extends string>({
  value,
  options,
  onValueChange,
  className,
  ...props
}: SelectProps<TValue>) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(event) => {
          const next = options.find((option) => option.value === event.target.value);
          if (next) onValueChange(next.value);
        }}
        className={cn(controlBase, "cursor-pointer appearance-none pr-10", className)}
        {...props}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value} className="bg-surface text-ink">
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-subtle"
      />
    </div>
  );
}
