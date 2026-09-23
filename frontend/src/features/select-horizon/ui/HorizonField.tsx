import { Clock3 } from "lucide-react";
import { useId } from "react";

import { HORIZON_OPTIONS, type HorizonHours } from "@/entities/forecast";
import { Field, SegmentedControl, type SegmentOption } from "@/shared/ui";

const OPTIONS: readonly SegmentOption<HorizonHours>[] = HORIZON_OPTIONS.map((hours) => ({
  value: hours,
  label: `${hours} ч`,
}));

type HorizonFieldProps = {
  value: HorizonHours;
  onChange: (value: HorizonHours) => void;
  disabled?: boolean;
};

export function HorizonField({ value, onChange, disabled }: HorizonFieldProps) {
  const labelId = useId();
  return (
    <Field label="Горизонт" labelId={labelId} icon={<Clock3 className="size-5" strokeWidth={1.4} />}>
      <SegmentedControl
        value={value}
        options={OPTIONS}
        onValueChange={onChange}
        ariaLabelledBy={labelId}
        disabled={disabled}
        size="sm"
        className="max-w-[170px]"
      />
    </Field>
  );
}
