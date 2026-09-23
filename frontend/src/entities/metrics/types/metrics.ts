import type { TurbineId } from "@/entities/turbine";
import type { IsoDate } from "@/shared/types";

export type ModelMetrics = {
  turbineId: TurbineId;
  mae: number;
  rmse: number;
  r2: number;
  /** Evaluated (origin, hour) pairs; null for demo values. */
  n: number | null;
};

/** "holdout" = real scores of the served model; "demo" = placeholders. */
export type MetricsSource = "demo" | "holdout";

export type MetricsEvaluation = {
  kind: string;
  periodStart: IsoDate;
  periodEnd: IsoDate;
  note: string;
};

export type ModelMetricsReport = {
  models: ModelMetrics[];
  source: MetricsSource;
  evaluation: MetricsEvaluation | null;
};
