import { ArrowDownToLine, ArrowUpToLine, Clock, Gauge, LayoutDashboard } from "lucide-react";
import { useMemo } from "react";

import { computeGenerationOutlook, computeTurbineStats, type ForecastResponse } from "@/entities/forecast";
import { formatDay, formatFixed, formatHour, formatPercent } from "@/shared/lib";
import { AnimatedNumber, Card, CardHeader, MetricCard, Skeleton } from "@/shared/ui";

import { GenerationOutlook } from "./GenerationOutlook";
import { TurbineBreakdown } from "./TurbineBreakdown";

type ForecastSummaryCardProps = {
  forecast: ForecastResponse | undefined;
  isLoading: boolean;
};

const EMPTY_VALUE = "—";

export function ForecastSummaryCard({ forecast, isLoading }: ForecastSummaryCardProps) {
  const summary = forecast?.summary ?? null;
  const turbineStats = useMemo(() => forecast?.turbines.map(computeTurbineStats) ?? [], [forecast]);
  const outlook = useMemo(
    () => (forecast?.turbines.length ? computeGenerationOutlook(forecast.turbines) : null),
    [forecast],
  );

  const renderPower = (value: number | undefined) =>
    value === undefined ? EMPTY_VALUE : <AnimatedNumber value={value} format={formatPercent} />;

  return (
    <Card className="h-full" aria-labelledby="summary-title">
      <CardHeader
        titleId="summary-title"
        title="Forecast summary"
        description="Normalized active power, share of rated capacity"
        icon={<LayoutDashboard className="size-4" aria-hidden />}
      />

      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="Average"
          icon={<Gauge className="size-3.5" aria-hidden />}
          value={renderPower(summary?.averagePower)}
          hint={summary ? `${formatFixed(summary.averagePower, 3)} normalized` : "Awaiting run"}
          isLoading={isLoading}
        />
        <MetricCard
          label="Peak hour"
          icon={<Clock className="size-3.5" aria-hidden />}
          value={summary ? formatHour(summary.peakHour) : EMPTY_VALUE}
          hint={summary ? formatDay(summary.peakHour) : "Awaiting run"}
          isLoading={isLoading}
        />
        <MetricCard
          label="Max"
          icon={<ArrowUpToLine className="size-3.5" aria-hidden />}
          value={renderPower(summary?.maxPower)}
          hint={summary ? `${formatFixed(summary.maxPower, 3)} normalized` : "Awaiting run"}
          isLoading={isLoading}
        />
        <MetricCard
          label="Min"
          icon={<ArrowDownToLine className="size-3.5" aria-hidden />}
          value={renderPower(summary?.minPower)}
          hint={summary ? `${formatFixed(summary.minPower, 3)} normalized` : "Awaiting run"}
          isLoading={isLoading}
        />
      </div>

      <div className="mt-5 border-t border-line pt-5">
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-8" />
            <Skeleton className="h-8" />
            <Skeleton className="h-16" />
          </div>
        ) : turbineStats.length > 0 ? (
          <div className="space-y-5">
            <TurbineBreakdown stats={turbineStats} />
            {outlook ? <GenerationOutlook outlook={outlook} /> : null}
          </div>
        ) : (
          <p className="text-sm text-ink-subtle">Per-turbine breakdown appears after the agent run.</p>
        )}
      </div>
    </Card>
  );
}
