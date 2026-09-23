import type { ForecastResponse } from "@/entities/forecast";

export type InsightTag = {
  key: string;
  label: string;
  tone: "neutral" | "good" | "warning";
};

/** 1 предупреждение · 2 предупреждения · 5 предупреждений */
function pluralWarnings(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "предупреждение";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "предупреждения";
  return "предупреждений";
}

function generationLevel(average: number): string {
  if (average >= 0.6) return "Высокая выработка";
  if (average >= 0.3) return "Умеренная выработка";
  return "Низкая выработка";
}

/** Short, factual tags derived from the agent's response (no invented signals). */
export function deriveInsightTags(forecast: ForecastResponse): InsightTag[] {
  const tags: InsightTag[] = [];
  if (forecast.summary) {
    tags.push({ key: "level", label: generationLevel(forecast.summary.averagePower), tone: "neutral" });
  }

  const recompute = forecast.agentSteps.find((step) => step.id === "recompute");
  if (recompute?.status === "completed") tags.push({ key: "recompute", label: "Выполнен пересчёт", tone: "warning" });
  else if (recompute?.status === "failed") tags.push({ key: "recompute", label: "Пересчёт не удался", tone: "warning" });
  else if (recompute?.status === "skipped" && forecast.status === "completed")
    tags.push({ key: "recompute", label: "Самопроверка пройдена", tone: "good" });

  const warnings = forecast.warnings.length;
  tags.push(
    warnings === 0
      ? { key: "warnings", label: "Аномалий нет", tone: "good" }
      : { key: "warnings", label: `${warnings} ${pluralWarnings(warnings)}`, tone: "warning" },
  );
  return tags;
}
