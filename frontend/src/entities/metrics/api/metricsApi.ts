import { isTurbineId } from "@/entities/turbine";
import { apiRequest } from "@/shared/api";

import type { MetricsEvaluation, MetricsSource, ModelMetrics, ModelMetricsReport } from "../types/metrics";

type ModelMetricsDto = {
  turbine_id: number;
  mae: number;
  rmse: number;
  r2: number;
  n: number | null;
};

type MetricsEvaluationDto = {
  kind: string;
  period_start: string;
  period_end: string;
  note: string;
};

type MetricsResponseDto = {
  models: ModelMetricsDto[];
  source: MetricsSource;
  evaluation: MetricsEvaluationDto | null;
};

function mapModelMetrics(dto: ModelMetricsDto): ModelMetrics | null {
  if (!isTurbineId(dto.turbine_id)) return null;
  return { turbineId: dto.turbine_id, mae: dto.mae, rmse: dto.rmse, r2: dto.r2, n: dto.n };
}

function mapEvaluation(dto: MetricsEvaluationDto): MetricsEvaluation {
  return { kind: dto.kind, periodStart: dto.period_start, periodEnd: dto.period_end, note: dto.note };
}

export async function fetchModelMetrics(signal?: AbortSignal): Promise<ModelMetricsReport> {
  const dto = await apiRequest<MetricsResponseDto>("/metrics", { signal });
  return {
    models: dto.models.map(mapModelMetrics).filter((model): model is ModelMetrics => model !== null),
    source: dto.source,
    evaluation: dto.evaluation ? mapEvaluation(dto.evaluation) : null,
  };
}
