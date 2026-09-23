import { palette } from "@/shared/config";

import type { TurbineId, TurbineMeta } from "../types/turbine";

export const TURBINE_IDS: readonly TurbineId[] = [1, 2];

export const TURBINES: Record<TurbineId, TurbineMeta> = {
  1: { id: 1, name: "Turbine 1", shortName: "T1", color: palette.series[0] },
  2: { id: 2, name: "Turbine 2", shortName: "T2", color: palette.series[1] },
};

export function isTurbineId(value: number): value is TurbineId {
  return value === 1 || value === 2;
}
