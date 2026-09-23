export type TurbineId = 1 | 2;

export type TurbineMeta = {
  id: TurbineId;
  name: string;
  shortName: string;
  /** Series color — follows the turbine everywhere, never its position in a list. */
  color: string;
};
