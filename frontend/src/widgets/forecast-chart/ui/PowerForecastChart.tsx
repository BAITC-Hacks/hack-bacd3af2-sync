import { Activity, LineChart } from "lucide-react";
import { motion } from "motion/react";
import { useMemo } from "react";

import { buildChartRows, type ForecastResponse } from "@/entities/forecast";
import { TURBINES } from "@/entities/turbine";
import { EASE_OUT_EXPO } from "@/shared/config";
import { formatLongDate } from "@/shared/lib";
import { Card, CardHeader, EmptyState, Skeleton } from "@/shared/ui";
import { ChartLegend } from "@/shared/ui/chart";

import { PowerChart } from "./PowerChart";

type PowerForecastChartProps = {
  forecast: ForecastResponse | undefined;
  isLoading: boolean;
};

export function PowerForecastChart({ forecast, isLoading }: PowerForecastChartProps) {
  const turbines = forecast?.turbines ?? [];
  const rows = useMemo(() => buildChartRows(turbines, "predictedPower"), [turbines]);
  const turbineIds = turbines.map((turbine) => turbine.turbineId);
  const hasData = rows.length > 0;

  const description = forecast
    ? `${formatLongDate(forecast.forecastDate)} · next ${forecast.horizonHours} hours`
    : "Hourly predicted power per turbine";

  return (
    <Card aria-labelledby="power-title" glow={hasData && !isLoading}>
      <CardHeader
        titleId="power-title"
        title="Power forecast"
        description={description}
        icon={<LineChart className="size-4" aria-hidden />}
        action={
          hasData ? (
            <ChartLegend
              items={turbineIds.map((id) => ({ key: String(id), label: TURBINES[id].name, color: TURBINES[id].color }))}
            />
          ) : null
        }
      />
      <div className="h-[300px] sm:h-[360px]">
        {isLoading ? (
          <Skeleton className="h-full" />
        ) : hasData && forecast ? (
          <motion.div
            key={forecast.generatedAt}
            className="h-full"
            initial={{ opacity: 0, clipPath: "inset(0 100% 0 0)" }}
            animate={{ opacity: 1, clipPath: "inset(0 0% 0 0)" }}
            transition={{ duration: 1.1, ease: EASE_OUT_EXPO }}
          >
            <PowerChart
              rows={rows}
              turbineIds={turbineIds}
              horizonHours={forecast.horizonHours}
              peakHour={forecast.summary?.peakHour}
            />
          </motion.div>
        ) : (
          <EmptyState
            icon={<Activity className="size-5" aria-hidden />}
            title={forecast?.status === "failed" ? "No forecast produced" : "No forecast yet"}
            description={
              forecast?.status === "failed"
                ? "The agent stopped before producing a forecast — see the agent status for details."
                : "Choose a date, turbines and horizon, then run the AI agent."
            }
          />
        )}
      </div>
    </Card>
  );
}
