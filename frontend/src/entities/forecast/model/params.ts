import { selectionToTurbineIds, type TurbineSelection } from "@/entities/turbine";

import type { ForecastRequest, HorizonHours } from "../types/forecast";

import { DEFAULT_FORECAST_DATE, DEFAULT_HORIZON } from "./constants";

/** Form-level forecast parameters as the user picks them. */
export type ForecastParams = {
  forecastDate: string;
  turbineSelection: TurbineSelection;
  horizonHours: HorizonHours;
};

export const DEFAULT_FORECAST_PARAMS: ForecastParams = {
  forecastDate: DEFAULT_FORECAST_DATE,
  turbineSelection: "both",
  horizonHours: DEFAULT_HORIZON,
};

export function toForecastRequest(params: ForecastParams): ForecastRequest {
  return {
    forecastDate: params.forecastDate,
    horizonHours: params.horizonHours,
    turbineIds: selectionToTurbineIds(params.turbineSelection),
  };
}
