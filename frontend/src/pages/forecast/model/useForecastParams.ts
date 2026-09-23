import { useCallback, useState } from "react";

import { DEFAULT_FORECAST_PARAMS, type ForecastParams } from "@/entities/forecast";

export function useForecastParams() {
  const [params, setParams] = useState<ForecastParams>(DEFAULT_FORECAST_PARAMS);
  const updateParams = useCallback((patch: Partial<ForecastParams>) => {
    setParams((current) => ({ ...current, ...patch }));
  }, []);
  return { params, updateParams };
}
