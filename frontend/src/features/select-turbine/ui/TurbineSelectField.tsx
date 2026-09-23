import { useId } from "react";

import type { TurbineSelection } from "@/entities/turbine";
import { Field, Select, TurbineMark, type SelectOption } from "@/shared/ui";

const TURBINE_OPTIONS: readonly SelectOption<TurbineSelection>[] = [
  { value: "both", label: "Обе турбины" },
  { value: "1", label: "Турбина 1" },
  { value: "2", label: "Турбина 2" },
];

type TurbineSelectFieldProps = {
  value: TurbineSelection;
  onChange: (value: TurbineSelection) => void;
  disabled?: boolean;
};

export function TurbineSelectField({ value, onChange, disabled }: TurbineSelectFieldProps) {
  const selectId = useId();
  return (
    <Field label="Турбины" htmlFor={selectId} icon={<TurbineMark className="h-6 w-5 text-cream/75" />}>
      <Select id={selectId} value={value} options={TURBINE_OPTIONS} onValueChange={onChange} disabled={disabled} />
    </Field>
  );
}
