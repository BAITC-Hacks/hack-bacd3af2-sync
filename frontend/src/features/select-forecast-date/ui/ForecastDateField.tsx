import { CalendarDays } from "lucide-react";
import { useId } from "react";

import { FORECAST_DATE_MAX, FORECAST_DATE_MIN } from "@/entities/forecast";
import { DateInput, Field } from "@/shared/ui";

type ForecastDateFieldProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
};

function clampToRange(value: string): string {
  if (value < FORECAST_DATE_MIN) return FORECAST_DATE_MIN;
  if (value > FORECAST_DATE_MAX) return FORECAST_DATE_MAX;
  return value;
}

export function ForecastDateField({ value, onChange, disabled }: ForecastDateFieldProps) {
  const inputId = useId();
  return (
    <Field label="Forecast date" htmlFor={inputId} icon={<CalendarDays className="size-3.5" aria-hidden />}>
      <DateInput
        id={inputId}
        value={value}
        min={FORECAST_DATE_MIN}
        max={FORECAST_DATE_MAX}
        disabled={disabled}
        onValueChange={(next) => onChange(clampToRange(next))}
      />
    </Field>
  );
}
