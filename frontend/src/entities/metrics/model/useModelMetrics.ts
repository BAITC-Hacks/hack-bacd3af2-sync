import { useQuery } from "@tanstack/react-query";

import type { ApiError } from "@/shared/api";

import { fetchModelMetrics } from "../api/metricsApi";
import type { ModelMetricsReport } from "../types/metrics";

export const modelMetricsQueryKey = ["model-metrics"] as const;

export function useModelMetrics() {
  return useQuery<ModelMetricsReport, ApiError>({
    queryKey: modelMetricsQueryKey,
    queryFn: ({ signal }) => fetchModelMetrics(signal),
    staleTime: 5 * 60_000,
  });
}
