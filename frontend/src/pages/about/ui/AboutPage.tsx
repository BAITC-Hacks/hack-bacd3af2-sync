import { Link } from "@tanstack/react-router";
import { ArrowRight, BrainCircuit, CloudSun, Cpu, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { AGENT_PIPELINE } from "@/entities/agent";
import { Card, Reveal } from "@/shared/ui";

type Pillar = { icon: ReactNode; title: string; text: string };

const PILLARS: Pillar[] = [
  {
    icon: <CloudSun className="size-4" aria-hidden />,
    title: "Weather service",
    text: "Fetches archived NWP forecasts (Open-Meteo Historical Forecast API) for each turbine location and shapes them into the model contract.",
  },
  {
    icon: <Cpu className="size-4" aria-hidden />,
    title: "ML adapter",
    text: "A single seam to the model: predict_power(turbine_id, weather, horizon_hours, forecast_origin). Mock today, CatBoost tomorrow — nothing else changes.",
  },
  {
    icon: <ShieldCheck className="size-4" aria-hidden />,
    title: "Guardrails",
    text: "Every step validates its output: schema, hourly continuity, physical ranges, NaNs, [0, 1] bounds. The agent repairs, warns or stops.",
  },
];

export function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl py-12 sm:py-16">
      <Reveal>
        <p className="text-sm font-medium text-accent">How it works</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
          An agent that owns the whole forecasting loop
        </h1>
        <p className="mt-4 text-ink-muted">
          WindAI forecasts hourly normalized active power of two wind turbines 24–48 hours ahead. Instead of a single
          model call, an agent orchestrates data retrieval, validation, inference and explanation — and reports what
          actually happened at each step.
        </p>
      </Reveal>

      <Reveal delay={0.1}>
        <Card className="mt-10">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold text-ink">
            <BrainCircuit className="size-4 text-accent" aria-hidden />
            Agent pipeline
          </h2>
          <ol className="mt-5 grid gap-3 sm:grid-cols-2">
            {AGENT_PIPELINE.map((stage, index) => (
              <li key={stage.id} className="flex gap-3 rounded-xl border border-line bg-white/[0.02] p-3.5">
                <span className="grid size-6 shrink-0 place-items-center rounded-full border border-cyan-400/30 bg-cyan-400/10 text-xs font-semibold text-accent tabular-nums">
                  {index + 1}
                </span>
                <span>
                  <span className="block text-sm font-medium text-ink">{stage.title}</span>
                  <span className="block text-[13px] text-ink-muted">{stage.description}</span>
                </span>
              </li>
            ))}
          </ol>
        </Card>
      </Reveal>

      <div className="mt-5 grid gap-5 md:grid-cols-3">
        {PILLARS.map((pillar, index) => (
          <Reveal key={pillar.title} delay={0.18 + index * 0.06}>
            <Card className="h-full">
              <span className="grid size-9 place-items-center rounded-xl border border-line bg-white/[0.04] text-accent">
                {pillar.icon}
              </span>
              <h3 className="mt-4 text-sm font-semibold text-ink">{pillar.title}</h3>
              <p className="mt-1.5 text-sm text-ink-muted">{pillar.text}</p>
            </Card>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.4}>
        <Link
          to="/forecast"
          className="mt-10 inline-flex items-center gap-2 text-sm font-medium text-accent hover:text-cyan-200"
        >
          Run a forecast <ArrowRight className="size-4" aria-hidden />
        </Link>
      </Reveal>
    </div>
  );
}
