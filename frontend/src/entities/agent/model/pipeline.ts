import type { AgentStep, AgentStepId } from "../types/agent";

type PipelineStage = {
  id: AgentStepId;
  title: string;
  description: string;
};

/**
 * The agent's plan, shown before a run has produced real step results.
 * Titles match the backend; statuses always come from the backend response.
 */
export const AGENT_PIPELINE: readonly PipelineStage[] = [
  { id: "fetch_weather", title: "Получение прогноза погоды", description: "Почасовые скорость ветра и температура для каждой турбины" },
  { id: "validate_weather", title: "Проверка погодных данных", description: "Схема, непрерывность, физические диапазоны, заполнение пропусков" },
  { id: "prepare_features", title: "Подготовка входных данных", description: "Таблицы по контракту для ML-модели" },
  { id: "run_model", title: "Запуск ML-модели", description: "Почасовая нормированная мощность по турбинам" },
  { id: "validate_prediction", title: "Проверка прогноза", description: "NaN, границы [0, 1], горизонт, аномалии" },
  { id: "analyze_result", title: "Анализ результата", description: "Самопроверка: обрезка, резервная погода, физика" },
  { id: "recompute", title: "Повторный расчёт", description: "Один перезапуск на свежих данных — только при необходимости" },
  { id: "generate_explanation", title: "Формирование объяснения", description: "Текстовый вывод по результатам прогноза" },
];

/** Russian step title by id (the backend reports titles in English). */
export function stepTitle(id: AgentStepId, fallback: string): string {
  return AGENT_PIPELINE.find((stage) => stage.id === id)?.title ?? fallback;
}

export function planAsPendingSteps(): AgentStep[] {
  return AGENT_PIPELINE.map((stage) => ({
    id: stage.id,
    title: stage.title,
    status: "pending",
    message: stage.description,
  }));
}
