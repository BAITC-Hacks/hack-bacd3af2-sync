const LOCALE = "ru-RU";

const timeFormatter = new Intl.DateTimeFormat(LOCALE, { hour: "2-digit", minute: "2-digit", hour12: false });
const dayFormatter = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short" });
const longDateFormatter = new Intl.DateTimeFormat(LOCALE, {
  weekday: "short",
  day: "numeric",
  month: "long",
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

const shortDateFormatter = new Intl.DateTimeFormat(LOCALE, { day: "numeric", month: "short", year: "numeric" });

/** "2025-12-01" → "1 дек. 2025 г." (parsed as a local calendar date, no timezone shift). */
export function formatShortDate(isoDate: string): string {
  return shortDateFormatter.format(new Date(`${isoDate}T00:00:00`));
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
  return ms < 1000 ? `${ms} мс` : `${(ms / 1000).toFixed(2).replace(".", ",")} с`;
}

export function formatRelativeTime(isoDateTime: string, now: Date = new Date()): string {
  const seconds = Math.round((now.getTime() - new Date(isoDateTime).getTime()) / 1000);
  if (seconds < 10) return "только что";
  if (seconds < 60) return `${seconds} с назад`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} мин назад` : new Date(isoDateTime).toLocaleString(LOCALE);
}
