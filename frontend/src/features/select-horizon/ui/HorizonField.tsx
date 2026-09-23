import { Clock } from "lucide-react";
import { useId } from "react";

import { HORIZON_OPTIONS, type HorizonHours } from "@/entities/forecast";
import { Field, SegmentedControl, type SegmentOption } from "@/shared/ui";

const OPTIONS: readonly SegmentOption<HorizonHours>[] = HORIZON_OPTIONS.map((hours) => ({
  value: hours,
  label: `${hours}h`,
}));

type HorizonFieldProps = {
  value: HorizonHours;
  onChange: (value: HorizonHours) => void;
  disabled?: boolean;
};

export function HorizonField({ value, onChange, disabled }: HorizonFieldProps) {
  const labelId = useId();
  return (
    <Field label="Horizon" labelId={labelId} icon={<Clock className="size-3.5" aria-hidden />}>
      <SegmentedControl
        value={value}
        options={OPTIONS}
        onValueChange={onChange}
        ariaLabelledBy={labelId}
        disabled={disabled}
      />
    </Field>
  );
}
