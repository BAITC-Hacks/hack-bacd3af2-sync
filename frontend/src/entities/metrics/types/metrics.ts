import type { TurbineId } from "@/entities/turbine";

export type ModelMetrics = {
  turbineId: TurbineId;
  mae: number;
  rmse: number;
  r2: number;
};

export type MetricsSource = "demo" | "file";

export type ModelMetricsReport = {
  models: ModelMetrics[];
  source: MetricsSource;
};
