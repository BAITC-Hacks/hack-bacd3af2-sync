import type { GenerationOutlook as Outlook } from "@/entities/forecast";
import { AnimatedNumber } from "@/shared/ui";

type GenerationOutlookProps = {
  outlook: Outlook;
};

const formatHours = (value: number) => `${Math.round(value)} h`;
const formatOneDecimalHours = (value: number) => `${value.toFixed(1)} h`;

export function GenerationOutlook({ outlook }: GenerationOutlookProps) {
  const items = [
    { label: "Full-load equivalent", value: outlook.fullLoadHours, format: formatOneDecimalHours },
    { label: "Hours ≥ 50% output", value: outlook.hoursAboveHalf, format: formatHours },
    { label: "Low-output hours (< 10%)", value: outlook.lowOutputHours, format: formatHours },
  ];
  return (
    <dl className="grid grid-cols-3 divide-x divide-line rounded-xl border border-line bg-white/[0.02]">
      {items.map((item) => (
        <div key={item.label} className="px-3 py-3 sm:px-4">
          <dt className="text-[11px] leading-tight text-ink-subtle">{item.label}</dt>
          <dd className="mt-1 text-lg font-semibold text-ink tabular-nums">
            <AnimatedNumber value={item.value} format={item.format} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
