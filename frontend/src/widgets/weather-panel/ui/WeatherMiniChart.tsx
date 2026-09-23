import { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";

import { hourlyTicks, paddedDomain, seriesKey, type ChartRow } from "@/entities/forecast";
import { TURBINES, type TurbineId } from "@/entities/turbine";
import { palette } from "@/shared/config";
import { formatDayHour, formatTimeTick, tickStepFor } from "@/shared/lib";
import { ChartTooltipCard } from "@/shared/ui/chart";

const AXIS_TICK = { fill: palette.inkSubtle, fontSize: 11 };

type WeatherMiniChartProps = {
  title: string;
  unit: string;
  rows: ChartRow[];
  turbineIds: TurbineId[];
  horizonHours: number;
  domainPadding: number;
};

function WeatherTooltip({
  active,
  label,
  rowsByTimestamp,
  turbineIds,
  unit,
}: Pick<TooltipContentProps<number, string>, "active" | "label"> & {
  rowsByTimestamp: Map<string, ChartRow>;
  turbineIds: TurbineId[];
  unit: string;
}) {
  if (!active || typeof label !== "string") return null;
  const row = rowsByTimestamp.get(label);
  if (!row) return null;
  const items = turbineIds.flatMap((id) => {
    const value = row[seriesKey(id)];
    if (value === undefined) return [];
    const turbine = TURBINES[id];
    return [{ key: turbine.name, label: turbine.name, color: turbine.color, value: `${value.toFixed(1)} ${unit}` }];
  });
  return <ChartTooltipCard title={formatDayHour(label)} items={items} />;
}

export function WeatherMiniChart({ title, unit, rows, turbineIds, horizonHours, domainPadding }: WeatherMiniChartProps) {
  const rowsByTimestamp = useMemo(() => new Map(rows.map((row) => [row.timestamp, row])), [rows]);
  const ticks = useMemo(() => hourlyTicks(rows, tickStepFor(horizonHours)), [rows, horizonHours]);
  const domain = useMemo(
    () => paddedDomain(rows, turbineIds.map(seriesKey), domainPadding),
    [rows, turbineIds, domainPadding],
  );

  return (
    <figure>
      <figcaption className="mb-2 flex items-baseline justify-between text-xs">
        <span className="font-medium text-ink-muted">{title}</span>
        <span className="text-ink-subtle">{unit}</span>
      </figcaption>
      <div className="h-36">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 4, right: 8, bottom: 0, left: -8 }}>
            <CartesianGrid vertical={false} stroke={palette.grid} />
            <XAxis
              dataKey="timestamp"
              ticks={ticks}
              tickFormatter={formatTimeTick}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: palette.axis }}
              tickMargin={8}
              minTickGap={12}
            />
            <YAxis domain={domain} tick={AXIS_TICK} tickLine={false} axisLine={false} width={48} tickCount={4} />
            <Tooltip
              cursor={{ stroke: palette.axis, strokeWidth: 1 }}
              content={(props) => (
                <WeatherTooltip
                  active={props.active}
                  label={props.label}
                  rowsByTimestamp={rowsByTimestamp}
                  turbineIds={turbineIds}
                  unit={unit}
                />
              )}
            />
            {turbineIds.map((id) => (
              <Line
                key={id}
                type="monotone"
                dataKey={seriesKey(id)}
                name={TURBINES[id].name}
                stroke={TURBINES[id].color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 2, stroke: palette.surface, fill: TURBINES[id].color }}
                animationDuration={900}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
