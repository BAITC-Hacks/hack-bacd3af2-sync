import { apiRequest } from "@/shared/api";

import type { ForecastRequest, ForecastResponse } from "../types/forecast";

import type { ForecastResponseDto } from "./dto";
import { mapForecastRequestToDto, mapForecastResponseDto } from "./mappers";

export async function createForecast(request: ForecastRequest, signal?: AbortSignal): Promise<ForecastResponse> {
  const dto = await apiRequest<ForecastResponseDto>("/forecast", {
    method: "POST",
    body: mapForecastRequestToDto(request),
    signal,
  });
  return mapForecastResponseDto(dto);
}
