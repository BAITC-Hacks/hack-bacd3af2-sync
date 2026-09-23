import type { AgentStep } from "@/entities/agent";
import type { TurbineId } from "@/entities/turbine";
import type { IsoDate, IsoDateTime } from "@/shared/types";

export type HorizonHours = 24 | 48;

export type ForecastRequest = {
  forecastDate: IsoDate;
  horizonHours: HorizonHours;
  turbineIds: TurbineId[];
};

export type ForecastPoint = {
  timestamp: IsoDateTime;
  predictedPower: number;
  windSpeed: number;
  temperature: number;
};

export type TurbineForecast = {
  turbineId: TurbineId;
  points: ForecastPoint[];
};

export type ForecastSummary = {
  averagePower: number;
  maxPower: number;
  minPower: number;
  peakHour: IsoDateTime;
};

export type ForecastStatus = "completed" | "failed";

export type ForecastResponse = {
  forecastDate: IsoDate;
  horizonHours: HorizonHours;
  generatedAt: IsoDateTime;
  status: ForecastStatus;
  /** null when the agent pipeline failed before producing a forecast. */
  summary: ForecastSummary | null;
  turbines: TurbineForecast[];
  agentSteps: AgentStep[];
  warnings: string[];
  explanation: string;
  modelVersion: string | null;
  weatherSource: string | null;
};
