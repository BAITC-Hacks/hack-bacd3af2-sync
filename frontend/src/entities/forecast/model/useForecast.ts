import { useMutation } from "@tanstack/react-query";

import type { ApiError } from "@/shared/api";

import { createForecast } from "../api/forecastApi";
import type { ForecastRequest, ForecastResponse } from "../types/forecast";

export const forecastMutationKey = ["forecast", "run"] as const;

/** Runs the forecasting agent. Each call is a new agent run, so this is a mutation, not a query. */
export function useRunForecast() {
  return useMutation<ForecastResponse, ApiError, ForecastRequest>({
    mutationKey: forecastMutationKey,
    mutationFn: (request) => createForecast(request),
  });
}
