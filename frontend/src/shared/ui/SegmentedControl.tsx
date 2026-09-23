import { motion } from "motion/react";
import { useId } from "react";

import { cn } from "@/shared/lib";

export type SegmentOption<TValue extends string | number> = {
  value: TValue;
  label: string;
};

type SegmentedControlProps<TValue extends string | number> = {
  value: TValue;
  options: readonly SegmentOption<TValue>[];
  onValueChange: (value: TValue) => void;
  ariaLabelledBy?: string;
  disabled?: boolean;
  className?: string;
};

export function SegmentedControl<TValue extends string | number>({
  value,
  options,
  onValueChange,
  ariaLabelledBy,
  disabled = false,
  className,
}: SegmentedControlProps<TValue>) {
  const indicatorId = useId();

  return (
    <div
      role="radiogroup"
      aria-labelledby={ariaLabelledBy}
      className={cn("flex h-11 rounded-xl border border-line bg-white/[0.035] p-1", disabled && "opacity-60", className)}
    >
      {options.map((option) => {
        const isActive = option.value === value;
        return (
          <button
            key={String(option.value)}
            type="button"
            role="radio"
            aria-checked={isActive}
            disabled={disabled}
            onClick={() => onValueChange(option.value)}
            className={cn(
              "relative flex-1 rounded-lg px-3 text-sm font-medium transition-colors",
              isActive ? "text-ink" : "text-ink-muted hover:text-ink",
            )}
          >
            {isActive ? (
              <motion.span
                layoutId={indicatorId}
                className="absolute inset-0 rounded-lg border border-cyan-400/30 bg-gradient-to-b from-cyan-400/15 to-violet-500/10"
                transition={{ type: "spring", stiffness: 420, damping: 36 }}
              />
            ) : null}
            <span className="relative">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
