import type { TurbineId } from "@/entities/turbine";

import type { ForecastPoint, TurbineForecast } from "../types/forecast";

export type SeriesKey = `turbine${TurbineId}`;

export type ChartRow = { timestamp: string } & Partial<Record<SeriesKey, number>>;

export type ForecastMetric = "predictedPower" | "windSpeed" | "temperature";

export function seriesKey(turbineId: TurbineId): SeriesKey {
  return `turbine${turbineId}`;
}

/** Pivot per-turbine points into one row per timestamp: { timestamp, turbine1, turbine2 }. */
export function buildChartRows(turbines: TurbineForecast[], metric: ForecastMetric): ChartRow[] {
  const rows = new Map<string, ChartRow>();
  for (const turbine of turbines) {
    const key = seriesKey(turbine.turbineId);
    for (const point of turbine.points) {
      const row = rows.get(point.timestamp) ?? { timestamp: point.timestamp };
      row[key] = point[metric];
      rows.set(point.timestamp, row);
    }
  }
  return [...rows.values()].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
}

export type TurbineStats = {
  turbineId: TurbineId;
  averagePower: number;
  peakPower: number;
  averageWind: number;
  averageTemperature: number;
};

function mean(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function pick(points: ForecastPoint[], metric: ForecastMetric): number[] {
  return points.map((point) => point[metric]);
}

export function computeTurbineStats(turbine: TurbineForecast): TurbineStats {
  const power = pick(turbine.points, "predictedPower");
  return {
    turbineId: turbine.turbineId,
    averagePower: mean(power),
    peakPower: power.length ? Math.max(...power) : 0,
    averageWind: mean(pick(turbine.points, "windSpeed")),
    averageTemperature: mean(pick(turbine.points, "temperature")),
  };
}

/** Symmetric-ish padded domain for weather charts so lines don't hug the plot edges. */
export function paddedDomain(rows: ChartRow[], keys: SeriesKey[], padding: number): [number, number] {
  const values = rows.flatMap((row) => keys.map((key) => row[key]).filter((v): v is number => v !== undefined));
  if (values.length === 0) return [0, 1];
  return [Math.floor(Math.min(...values) - padding), Math.ceil(Math.max(...values) + padding)];
}

/** Ticks every `stepHours`, always including the first timestamp. */
export function hourlyTicks(rows: ChartRow[], stepHours: number): string[] {
  return rows.filter((_, index) => index % stepHours === 0).map((row) => row.timestamp);
}

export type GenerationOutlook = {
  /** Sum of fleet-average normalized power: hours of rated output the forecast is equivalent to. */
  fullLoadHours: number;
  hoursAboveHalf: number;
  lowOutputHours: number;
};

const HALF_LOAD = 0.5;
const LOW_OUTPUT = 0.1;

export function computeGenerationOutlook(turbines: TurbineForecast[]): GenerationOutlook {
  const fleet = buildChartRows(turbines, "predictedPower").map((row) =>
    mean(turbines.map((turbine) => row[seriesKey(turbine.turbineId)]).filter((v): v is number => v !== undefined)),
  );
  return {
    fullLoadHours: fleet.reduce((sum, value) => sum + value, 0),
    hoursAboveHalf: fleet.filter((value) => value >= HALF_LOAD).length,
    lowOutputHours: fleet.filter((value) => value < LOW_OUTPUT).length,
  };
}

export type SiteRow = { timestamp: string; value: number };

/** Hourly mean of a weather metric across the forecast's turbines (they share the NWP grid cell). */
export function buildSiteAverageRows(turbines: TurbineForecast[], metric: ForecastMetric): SiteRow[] {
  return buildChartRows(turbines, metric).map((row) => {
    const values = turbines
      .map((turbine) => row[seriesKey(turbine.turbineId)])
      .filter((value): value is number => value !== undefined);
    return { timestamp: row.timestamp, value: mean(values) };
  });
}
