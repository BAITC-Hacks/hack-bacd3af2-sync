import { motion } from "motion/react";

import type { TurbineStats } from "@/entities/forecast";
import { TURBINES } from "@/entities/turbine";
import { EASE_OUT_EXPO } from "@/shared/config";
import { formatPercent } from "@/shared/lib";

type TurbineBreakdownProps = {
  stats: TurbineStats[];
};

export function TurbineBreakdown({ stats }: TurbineBreakdownProps) {
  return (
    <ul className="space-y-3">
      {stats.map((item, index) => {
        const turbine = TURBINES[item.turbineId];
        return (
          <li key={item.turbineId}>
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-2 font-medium text-ink">
                <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: turbine.color }} />
                {turbine.name}
              </span>
              <span className="text-xs text-ink-muted tabular-nums">
                avg <span className="text-ink">{formatPercent(item.averagePower)}</span> · wind{" "}
                <span className="text-ink">{item.averageWind.toFixed(1)} m/s</span> ·{" "}
                <span className="text-ink">{item.averageTemperature.toFixed(0)} °C</span>
              </span>
            </div>
            <div
              className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/[0.05]"
              role="meter"
              aria-label={`${turbine.name} average output`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round(item.averagePower * 100)}
            >
              <motion.div
                className="h-full rounded-full"
                style={{ backgroundColor: turbine.color }}
                initial={{ width: 0 }}
                animate={{ width: `${item.averagePower * 100}%` }}
                transition={{ duration: 1, delay: 0.15 + index * 0.1, ease: EASE_OUT_EXPO }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
