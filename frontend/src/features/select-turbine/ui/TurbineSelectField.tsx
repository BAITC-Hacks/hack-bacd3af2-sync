import { Fan } from "lucide-react";
import { useId } from "react";

import type { TurbineSelection } from "@/entities/turbine";
import { Field, Select, type SelectOption } from "@/shared/ui";

const TURBINE_OPTIONS: readonly SelectOption<TurbineSelection>[] = [
  { value: "both", label: "Both turbines" },
  { value: "1", label: "Turbine 1" },
  { value: "2", label: "Turbine 2" },
];

type TurbineSelectFieldProps = {
  value: TurbineSelection;
  onChange: (value: TurbineSelection) => void;
  disabled?: boolean;
};

export function TurbineSelectField({ value, onChange, disabled }: TurbineSelectFieldProps) {
  const selectId = useId();
  return (
    <Field label="Turbine" htmlFor={selectId} icon={<Fan className="size-3.5" aria-hidden />}>
      <Select id={selectId} value={value} options={TURBINE_OPTIONS} onValueChange={onChange} disabled={disabled} />
    </Field>
  );
}
