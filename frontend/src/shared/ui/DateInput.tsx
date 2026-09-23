import type { InputHTMLAttributes } from "react";

import { cn } from "@/shared/lib";

import { controlBase } from "./controlStyles";

type DateInputProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "value" | "onChange"> & {
  value: string;
  onValueChange: (value: string) => void;
};

export function DateInput({ value, onValueChange, className, ...props }: DateInputProps) {
  return (
    <input
      type="date"
      value={value}
      onChange={(event) => {
        if (event.target.value) onValueChange(event.target.value);
      }}
      className={cn(
        controlBase,
        "tabular-nums [color-scheme:dark] [&::-webkit-calendar-picker-indicator]:cursor-pointer [&::-webkit-calendar-picker-indicator]:opacity-70 [&::-webkit-calendar-picker-indicator]:[filter:sepia(0.6)_saturate(0.6)]",
        className,
      )}
      {...props}
    />
  );
}
