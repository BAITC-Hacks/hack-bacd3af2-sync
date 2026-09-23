import { isTurbineId } from "@/entities/turbine";
import { apiRequest } from "@/shared/api";

import type { MetricsSource, ModelMetrics, ModelMetricsReport } from "../types/metrics";

type ModelMetricsDto = {
  turbine_id: number;
  mae: number;
  rmse: number;
  r2: number;
};

type MetricsResponseDto = {
  models: ModelMetricsDto[];
  source: MetricsSource;
};

function mapModelMetrics(dto: ModelMetricsDto): ModelMetrics | null {
  if (!isTurbineId(dto.turbine_id)) return null;
  return { turbineId: dto.turbine_id, mae: dto.mae, rmse: dto.rmse, r2: dto.r2 };
}

export async function fetchModelMetrics(signal?: AbortSignal): Promise<ModelMetricsReport> {
  const dto = await apiRequest<MetricsResponseDto>("/metrics", { signal });
  return {
    models: dto.models.map(mapModelMetrics).filter((model): model is ModelMetrics => model !== null),
    source: dto.source,
  };
}
