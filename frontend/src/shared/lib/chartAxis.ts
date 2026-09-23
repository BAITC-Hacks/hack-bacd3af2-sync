import { formatDay, formatHour } from "./format";

/** Midnight ticks show the day ("Feb 02"), other ticks the hour ("06:00"). */
export function formatTimeTick(value: string): string {
  const hour = formatHour(value);
  return hour === "00:00" ? formatDay(value) : hour;
}

export function tickStepFor(horizonHours: number): number {
  return horizonHours > 24 ? 6 : 3;
}
