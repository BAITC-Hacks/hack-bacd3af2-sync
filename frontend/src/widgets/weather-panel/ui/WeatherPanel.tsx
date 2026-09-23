import { CloudSun } from "lucide-react";
import { motion } from "motion/react";
import { useMemo } from "react";

import { buildChartRows, type ForecastResponse } from "@/entities/forecast";
import { TURBINES } from "@/entities/turbine";
import { baseTransition } from "@/shared/config";
import { Card, CardHeader, EmptyState, Skeleton } from "@/shared/ui";
import { ChartLegend } from "@/shared/ui/chart";

import { WeatherMiniChart } from "./WeatherMiniChart";

type WeatherPanelProps = {
  forecast: ForecastResponse | undefined;
  isLoading: boolean;
};

export function WeatherPanel({ forecast, isLoading }: WeatherPanelProps) {
  const turbines = forecast?.turbines ?? [];
  const windRows = useMemo(() => buildChartRows(turbines, "windSpeed"), [turbines]);
  const temperatureRows = useMemo(() => buildChartRows(turbines, "temperature"), [turbines]);
  const turbineIds = turbines.map((turbine) => turbine.turbineId);
  const hasData = windRows.length > 0 && forecast !== undefined;

  return (
    <Card className="h-full" aria-labelledby="weather-title">
      <CardHeader
        titleId="weather-title"
        title="Weather features"
        description="Model inputs at each turbine location"
        icon={<CloudSun className="size-4" aria-hidden />}
        action={
          hasData && turbineIds.length > 1 ? (
            <ChartLegend
              items={turbineIds.map((id) => ({ key: String(id), label: TURBINES[id].name, color: TURBINES[id].color }))}
            />
          ) : null
        }
      />
      {isLoading ? (
        <div className="space-y-5">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : hasData ? (
        <motion.div
          key={forecast.generatedAt}
          className="space-y-5"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={baseTransition}
        >
          <WeatherMiniChart
            title="Wind speed"
            unit="m/s"
            rows={windRows}
            turbineIds={turbineIds}
            horizonHours={forecast.horizonHours}
            domainPadding={1}
          />
          <WeatherMiniChart
            title="Temperature"
            unit="°C"
            rows={temperatureRows}
            turbineIds={turbineIds}
            horizonHours={forecast.horizonHours}
            domainPadding={2}
          />
        </motion.div>
      ) : (
        <EmptyState
          className="min-h-80"
          icon={<CloudSun className="size-5" aria-hidden />}
          title="No weather loaded"
          description="The agent retrieves hourly wind speed and temperature for each turbine during a run."
        />
      )}
    </Card>
  );
}
