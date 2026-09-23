import { motion } from "motion/react";

import type { ForecastParams } from "@/entities/forecast";
import { RunForecastButton } from "@/features/run-forecast";
import { ForecastDateField } from "@/features/select-forecast-date";
import { HorizonField } from "@/features/select-horizon";
import { TurbineSelectField } from "@/features/select-turbine";
import { baseTransition } from "@/shared/config";
import { Badge } from "@/shared/ui";

import { WindStreaks } from "./WindStreaks";

type ForecastControlsProps = {
  params: ForecastParams;
  onParamsChange: (patch: Partial<ForecastParams>) => void;
  onRun: () => void;
  isRunning: boolean;
};

export function ForecastControls({ params, onParamsChange, onRun, isRunning }: ForecastControlsProps) {
  return (
    <section aria-labelledby="hero-title" className="relative pt-10 pb-2 sm:pt-14">
      <WindStreaks />
      <motion.div
        className="relative"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={baseTransition}
      >
        <Badge tone="accent">
          <span className="size-1.5 rounded-full bg-accent animate-pulse-soft" aria-hidden />
          Agentic AI · Hourly forecast · 24–48 h horizon
        </Badge>
        <h1 id="hero-title" className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
          <span className="text-gradient">WindAI</span>
        </h1>
        <p className="mt-3 max-w-2xl text-base text-ink-muted sm:text-lg">
          Agentic AI forecasting for wind power generation. Pick a date, turbines and horizon — the agent fetches
          weather, validates it, runs the model and explains the result.
        </p>
      </motion.div>

      <motion.div
        className="glass relative mt-8 grid gap-4 rounded-2xl p-4 sm:grid-cols-2 sm:p-5 lg:grid-cols-[1fr_1fr_0.9fr_auto] lg:items-end"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ ...baseTransition, delay: 0.12 }}
      >
        <ForecastDateField
          value={params.forecastDate}
          onChange={(forecastDate) => onParamsChange({ forecastDate })}
          disabled={isRunning}
        />
        <TurbineSelectField
          value={params.turbineSelection}
          onChange={(turbineSelection) => onParamsChange({ turbineSelection })}
          disabled={isRunning}
        />
        <HorizonField
          value={params.horizonHours}
          onChange={(horizonHours) => onParamsChange({ horizonHours })}
          disabled={isRunning}
        />
        <RunForecastButton onRun={onRun} isRunning={isRunning} className="w-full sm:col-span-2 lg:col-span-1" />
      </motion.div>
    </section>
  );
}
