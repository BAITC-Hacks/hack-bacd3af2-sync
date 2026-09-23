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
  ariaLabel?: string;
  disabled?: boolean;
  /** "solid": cream fill (primary choice). "subtle": raised olive pill (view filters). */
  variant?: "solid" | "subtle";
  size?: "sm" | "md";
  className?: string;
};

export function SegmentedControl<TValue extends string | number>({
  value,
  options,
  onValueChange,
  ariaLabelledBy,
  ariaLabel,
  disabled = false,
  variant = "solid",
  size = "md",
  className,
}: SegmentedControlProps<TValue>) {
  const indicatorId = useId();

  return (
    <div
      role="radiogroup"
      aria-labelledby={ariaLabelledBy}
      aria-label={ariaLabel}
      className={cn(
        "field flex rounded-[10px] p-[3px]",
        size === "sm" ? "h-8" : "h-9",
        disabled && "opacity-60",
        className,
      )}
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
              "relative flex-1 rounded-[7px] px-3 font-medium whitespace-nowrap transition-colors duration-200",
              size === "sm" ? "text-[12px]" : "text-[13px]",
              isActive
                ? variant === "solid"
                  ? "text-[#1b1a14]"
                  : "text-ink"
                : "text-ink-muted hover:text-ink",
            )}
          >
            {isActive ? (
              <motion.span
                layoutId={indicatorId}
                className={cn(
                  "absolute inset-0 rounded-[7px]",
                  variant === "solid"
                    ? "bg-gradient-to-b from-cream-strong to-[#d4ba8c]"
                    : "border border-line-strong bg-[#2a2920]",
                )}
                transition={{ type: "spring", stiffness: 420, damping: 38 }}
              />
            ) : null}
            <span className="relative">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
