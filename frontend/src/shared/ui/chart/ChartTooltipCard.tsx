import { SeriesMarker } from "./SeriesMarker";

export type ChartTooltipItem = {
  key: string;
  label: string;
  color: string;
  shape: "dot" | "ring";
  value: string;
};

type ChartTooltipCardProps = {
  title: string;
  items: ChartTooltipItem[];
  footer?: string;
};

/** Presentational tooltip body shared by all charts (values in ink, color only on the marker). */
export function ChartTooltipCard({ title, items, footer }: ChartTooltipCardProps) {
  return (
    <div className="min-w-40 rounded-[10px] border border-line-strong bg-[#171812]/95 px-3 py-2.5 shadow-[0_18px_40px_-18px_rgb(0_0_0/0.9)] backdrop-blur-md">
      <p className="text-[11.5px] text-ink-muted tabular-nums">{title}</p>
      <ul className="mt-1.5 space-y-1">
        {items.map((item) => (
          <li key={item.key} className="flex items-center justify-between gap-5 text-[12.5px]">
            <span className="flex items-center gap-2 text-ink-muted">
              <SeriesMarker color={item.color} shape={item.shape} className="size-2" />
              {item.label}
            </span>
            <span className="font-medium text-ink tabular-nums">{item.value}</span>
          </li>
        ))}
      </ul>
      {footer ? <p className="mt-2 border-t border-line pt-1.5 text-[11px] text-ink-subtle">{footer}</p> : null}
    </div>
  );
}
