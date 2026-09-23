export type ChartTooltipItem = {
  key: string;
  label: string;
  color: string;
  value: string;
};

type ChartTooltipCardProps = {
  title: string;
  items: ChartTooltipItem[];
  footer?: string;
};

/** Presentational tooltip body shared by all charts (values in ink, color only on the swatch). */
export function ChartTooltipCard({ title, items, footer }: ChartTooltipCardProps) {
  return (
    <div className="min-w-44 rounded-xl border border-line-strong bg-surface-raised/95 px-3.5 py-3 shadow-2xl backdrop-blur-md">
      <p className="text-xs font-medium text-ink-muted">{title}</p>
      <ul className="mt-2 space-y-1.5">
        {items.map((item) => (
          <li key={item.key} className="flex items-center justify-between gap-6 text-sm">
            <span className="flex items-center gap-2 text-ink-muted">
              <span aria-hidden className="h-0.5 w-3 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
            <span className="font-medium text-ink tabular-nums">{item.value}</span>
          </li>
        ))}
      </ul>
      {footer ? <p className="mt-2 border-t border-line pt-2 text-xs text-ink-subtle">{footer}</p> : null}
    </div>
  );
}
