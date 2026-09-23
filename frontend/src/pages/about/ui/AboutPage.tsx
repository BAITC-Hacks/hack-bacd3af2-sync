import { Link } from "@tanstack/react-router";
import { ArrowRight, BrainCircuit, CloudSun, Cpu, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import { AGENT_PIPELINE } from "@/entities/agent";
import { Card, Reveal } from "@/shared/ui";

type Pillar = { icon: ReactNode; title: string; text: string };

const PILLARS: Pillar[] = [
  {
    icon: <CloudSun className="size-4" aria-hidden />,
    title: "Погодный сервис",
    text: "Получает почасовую погоду для координат каждой турбины и приводит её к контракту модели. Дашборд использует Open-Meteo Historical Forecast, строгий бэктест без утечки — архивные прогоны Single Runs (ECMWF IFS).",
  },
  {
    icon: <Cpu className="size-4" aria-hidden />,
    title: "ML-адаптер",
    text: "Единая точка связи с моделью: predict_power(turbine_id, weather, horizon_hours, forecast_origin). Для каждой даты выбирается CatBoost-модель, обученная строго до неё.",
  },
  {
    icon: <ShieldCheck className="size-4" aria-hidden />,
    title: "Контроль качества",
    text: "Каждый шаг проверяет свой результат: схему, почасовую непрерывность, физические диапазоны, NaN, границы [0, 1]. Агент исправляет данные, предупреждает или останавливается.",
  },
];

export function AboutPage() {
  return (
    <div className="mx-auto max-w-4xl py-12 sm:py-16">
      <Reveal>
        <p className="eyebrow">Методология</p>
        <h1 className="mt-3 font-display text-[40px] leading-tight text-ink sm:text-[52px]">
          Агент, который ведёт весь цикл прогноза
        </h1>
        <p className="mt-4 text-ink-muted">
          WindAI прогнозирует почасовую нормированную активную мощность двух ветротурбин на 24–48 часов вперёд.
          Вместо одного вызова модели агент управляет получением данных, проверкой, расчётом, самоанализом и
          объяснением — и сообщает, что на самом деле произошло на каждом шаге.
        </p>
      </Reveal>

      <Reveal delay={0.1}>
        <Card className="mt-10">
          <h2 className="flex items-center gap-2.5 font-display text-[22px] text-ink">
            <BrainCircuit className="size-4 text-accent" aria-hidden />
            Конвейер агента
          </h2>
          <ol className="mt-5 grid gap-3 sm:grid-cols-2">
            {AGENT_PIPELINE.map((stage, index) => (
              <li key={stage.id} className="flex gap-3 rounded-xl border border-line bg-panel-soft p-3.5">
                <span className="grid size-6 shrink-0 place-items-center rounded-full border border-cream/30 bg-cream/[0.06] text-xs text-cream tabular-nums">
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
              <span className="text-cream/80">
                {pillar.icon}
              </span>
              <h3 className="mt-3 font-display text-[19px] text-ink">{pillar.title}</h3>
              <p className="mt-1.5 text-sm text-ink-muted">{pillar.text}</p>
            </Card>
          </Reveal>
        ))}
      </div>

      <Reveal delay={0.4}>
        <Link
          to="/forecast"
          className="mt-10 inline-flex items-center gap-2 text-sm font-medium text-cream hover:text-cream-strong"
        >
          Запустить прогноз <ArrowRight className="size-4" aria-hidden />
        </Link>
      </Reveal>
    </div>
  );
}
