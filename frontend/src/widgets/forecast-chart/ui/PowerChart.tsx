import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";

import { hourlyTicks, seriesKey, type ChartRow } from "@/entities/forecast";
import { TURBINES, type TurbineId } from "@/entities/turbine";
import { palette } from "@/shared/config";
import { formatDayHour, formatFixed, formatPercent, formatTimeTick, tickStepFor } from "@/shared/lib";
import { ChartTooltipCard } from "@/shared/ui/chart";


const Y_TICKS = [0, 0.25, 0.5, 0.75, 1];
const AXIS_TICK = { fill: palette.inkSubtle, fontSize: 11 };

type PowerChartProps = {
  rows: ChartRow[];
  turbineIds: TurbineId[];
  horizonHours: number;
  peakHour: string | undefined;
};

function PowerTooltip({
  active,
  label,
  rowsByTimestamp,
  turbineIds,
}: Pick<TooltipContentProps<number, string>, "active" | "label"> & {
  rowsByTimestamp: Map<string, ChartRow>;
  turbineIds: TurbineId[];
}) {
  if (!active || typeof label !== "string") return null;
  const row = rowsByTimestamp.get(label);
  if (!row) return null;

  const items = turbineIds.flatMap((id) => {
    const value = row[seriesKey(id)];
    if (value === undefined) return [];
    const turbine = TURBINES[id];
    return [{ key: turbine.name, label: turbine.name, color: turbine.color, value: `${formatFixed(value, 3)} · ${formatPercent(value)}` }];
  });
  return <ChartTooltipCard title={formatDayHour(label)} items={items} footer="Normalized active power (0–1)" />;
}

export function PowerChart({ rows, turbineIds, horizonHours, peakHour }: PowerChartProps) {
  const rowsByTimestamp = useMemo(() => new Map(rows.map((row) => [row.timestamp, row])), [rows]);
  const ticks = useMemo(() => hourlyTicks(rows, tickStepFor(horizonHours)), [rows, horizonHours]);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={rows} margin={{ top: 24, right: 8, bottom: 0, left: -8 }}>
        <defs>
          {turbineIds.map((id) => (
            <linearGradient key={id} id={`power-fill-${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={TURBINES[id].color} stopOpacity={0.22} />
              <stop offset="100%" stopColor={TURBINES[id].color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid vertical={false} stroke={palette.grid} />
        <XAxis
          dataKey="timestamp"
          ticks={ticks}
          tickFormatter={formatTimeTick}
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={{ stroke: palette.axis }}
          tickMargin={10}
          minTickGap={12}
        />
        <YAxis
          domain={[0, 1]}
          ticks={Y_TICKS}
          allowDataOverflow
          tickFormatter={(value: number) => value.toFixed(2)}
          tick={AXIS_TICK}
          tickLine={false}
          axisLine={false}
          width={48}
        />
        <Tooltip
          cursor={{ stroke: palette.axis, strokeWidth: 1 }}
          content={(props) => (
            <PowerTooltip
              active={props.active}
              label={props.label}
              rowsByTimestamp={rowsByTimestamp}
              turbineIds={turbineIds}
            />
          )}
        />
        {peakHour ? (
          <ReferenceLine
            x={peakHour}
            stroke={palette.accent}
            strokeOpacity={0.45}
            label={{ value: "Peak", position: "top", fill: palette.inkMuted, fontSize: 11 }}
          />
        ) : null}
        {turbineIds.map((id) => (
          <Area
            key={id}
            type="monotone"
            dataKey={seriesKey(id)}
            name={TURBINES[id].name}
            stroke={TURBINES[id].color}
            strokeWidth={2}
            fill={`url(#power-fill-${id})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: palette.surface, fill: TURBINES[id].color }}
            animationDuration={900}
            animationEasing="ease-out"
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
