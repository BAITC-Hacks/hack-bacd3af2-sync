const timeFormatter = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", hour12: false });
const dayFormatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "2-digit" });
const longDateFormatter = new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
});

/** Backend timestamps are naive wall-clock ISO strings; parsing without a zone keeps them local. */
export function parseTimestamp(value: string): Date {
  return new Date(value);
}

export function formatHour(value: string): string {
  return timeFormatter.format(parseTimestamp(value));
}

export function formatDay(value: string): string {
  return dayFormatter.format(parseTimestamp(value));
}

export function formatDayHour(value: string): string {
  return `${formatDay(value)}, ${formatHour(value)}`;
}

export function formatLongDate(isoDate: string): string {
  return longDateFormatter.format(new Date(`${isoDate}T00:00:00`));
}

/** Normalized power 0..1 → "57%". */
export function formatPercent(value: number, fractionDigits = 0): string {
  return `${(value * 100).toFixed(fractionDigits)}%`;
}

export function formatFixed(value: number, fractionDigits = 2): string {
  return value.toFixed(fractionDigits);
}

export function formatDuration(ms: number): string {
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(2)} s`;
}

export function formatRelativeTime(isoDateTime: string, now: Date = new Date()): string {
  const seconds = Math.round((now.getTime() - new Date(isoDateTime).getTime()) / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} min ago` : new Date(isoDateTime).toLocaleString();
}
