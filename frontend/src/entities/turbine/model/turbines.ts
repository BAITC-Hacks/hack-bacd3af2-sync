import { palette } from "@/shared/config";

import type { TurbineId, TurbineMeta } from "../types/turbine";

export const TURBINE_IDS: readonly TurbineId[] = [1, 2];

export const TURBINES: Record<TurbineId, TurbineMeta> = {
  1: { id: 1, name: "Турбина 1", shortName: "Т1", color: palette.series[0], marker: "dot" },
  2: { id: 2, name: "Турбина 2", shortName: "Т2", color: palette.series[1], marker: "ring" },
};

export function isTurbineId(value: number): value is TurbineId {
  return value === 1 || value === 2;
}
