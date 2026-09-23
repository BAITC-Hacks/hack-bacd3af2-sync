import type { TurbineId } from "../types/turbine";

/** What the user picks in the UI; mapped to turbine ids for the API. */
export type TurbineSelection = "1" | "2" | "both";

const SELECTION_TO_IDS: Record<TurbineSelection, TurbineId[]> = {
  "1": [1],
  "2": [2],
  both: [1, 2],
};

export function selectionToTurbineIds(selection: TurbineSelection): TurbineId[] {
  return SELECTION_TO_IDS[selection];
}
