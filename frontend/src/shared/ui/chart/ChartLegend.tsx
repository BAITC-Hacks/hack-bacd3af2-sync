import { cn } from "@/shared/lib";

export type ChartLegendItem = {
  key: string;
  label: string;
  color: string;
};

type ChartLegendProps = {
  items: ChartLegendItem[];
  className?: string;
};

export function ChartLegend({ items, className }: ChartLegendProps) {
  return (
    <ul className={cn("flex flex-wrap items-center gap-x-4 gap-y-1", className)} aria-label="Chart legend">
      {items.map((item) => (
        <li key={item.key} className="flex items-center gap-2 text-xs text-ink-muted">
          <span aria-hidden className="h-0.5 w-4 rounded-full" style={{ backgroundColor: item.color }} />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
