import { ArrowRight, Database } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useId, useState } from "react";

import { useModelMetrics, type ModelMetricsReport } from "@/entities/metrics";
import { TURBINES } from "@/entities/turbine";
import { formatShortDate } from "@/shared/lib";
import { Skeleton } from "@/shared/ui";
import { SeriesMarker } from "@/shared/ui/chart";

const COLUMNS = [
  { key: "mae", label: "MAE", digits: 3, hint: "Средняя абсолютная ошибка: чем меньше, тем лучше" },
  { key: "rmse", label: "RMSE", digits: 3, hint: "Среднеквадратичная ошибка: чем меньше, тем лучше" },
  { key: "r2", label: "R²", digits: 2, hint: "Объяснённая дисперсия: чем ближе к 1, тем лучше" },
] as const;

function caption(report: ModelMetricsReport | undefined): string {
  if (!report) return "";
  return report.source === "holdout" ? "Отложенная выборка · наблюдённая погода" : "Демо-значения · mock-модель";
}

// Russian wording of the evaluation caveat, keyed by the backend's evaluation kind.
const EVALUATION_NOTES: Record<string, string> = {
  observed_weather_proxy:
    "Метрики модели мощности на отложенном периоде с наблюдённой погодой. Это не операционная точность: ошибка прогноза погоды в них не учтена.",
};

/** Model Metrics section (rendered inside the right-column card). */
export function ModelMetrics() {
  const { data, isPending, isError, error } = useModelMetrics();
  const [showDetails, setShowDetails] = useState(false);
  const detailsId = useId();

  return (
    <section aria-labelledby="metrics-title">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="metrics-title" className="flex items-center gap-3 font-display text-[19px] text-ink">
          <Database className="size-5 text-cream/80" strokeWidth={1.4} aria-hidden />
          Метрики модели
        </h2>
        <button
          type="button"
          onClick={() => setShowDetails((open) => !open)}
          aria-expanded={showDetails}
          aria-controls={detailsId}
          className="flex h-7 items-center gap-1.5 rounded-lg border border-line px-2.5 text-[11.5px] text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
        >
          Детали
          <ArrowRight className={`size-3 transition-transform ${showDetails ? "rotate-90" : ""}`} aria-hidden />
        </button>
      </div>

      {isPending ? (
        <div className="space-y-2">
          <Skeleton className="h-6" />
          <Skeleton className="h-6" />
        </div>
      ) : isError ? (
        <p role="alert" className="text-[12.5px] text-ink-muted">
          Метрики недоступны: {error.message}
        </p>
      ) : (
        <>
          <table className="w-full text-[12.5px]">
            <caption className="sr-only">Метрики ошибки модели по турбинам</caption>
            <thead>
              <tr className="text-[11.5px] text-ink-subtle">
                <th scope="col" className="pb-1.5 text-left font-normal">
                  Турбина
                </th>
                {COLUMNS.map((column) => (
                  <th key={column.key} scope="col" title={column.hint} className="pb-1.5 text-right font-normal">
                    {column.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.models.map((model) => {
                const turbine = TURBINES[model.turbineId];
                return (
                  <tr key={model.turbineId}>
                    <th scope="row" className="py-1.5 text-left font-normal text-ink">
                      <span className="flex items-center gap-2">
                        <SeriesMarker color={turbine.color} shape={turbine.marker} className="size-2" />
                        {turbine.name}
                      </span>
                    </th>
                    {COLUMNS.map((column) => (
                      <td key={column.key} className="py-1.5 text-right text-ink tabular-nums">
                        {model[column.key].toFixed(column.digits)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] text-ink-subtle">{caption(data)}</p>

          <AnimatePresence initial={false}>
            {showDetails ? (
              <motion.div
                id={detailsId}
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.25 }}
                className="overflow-hidden"
              >
                <div className="mt-3 space-y-2 border-t border-line pt-3 text-[11.5px] leading-relaxed text-ink-muted">
                  {data.evaluation ? (
                    <>
                      <p>
                        Отложенный период: {formatShortDate(data.evaluation.periodStart)} – {formatShortDate(data.evaluation.periodEnd)}
                        {data.models[0]?.n != null ? ` · n = ${data.models.map((m) => m.n?.toLocaleString("ru-RU")).join(" / ")}` : ""}
                      </p>
                      <p>{EVALUATION_NOTES[data.evaluation.kind] ?? data.evaluation.note}</p>
                    </>
                  ) : (
                    <p>Демо-значения. Запустите сервер с MODEL_ADAPTER=real, чтобы увидеть метрики CatBoost на отложенной выборке.</p>
                  )}
                  <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-ink-subtle">
                    {COLUMNS.map((column) => (
                      <div key={column.key} className="contents">
                        <dt className="text-ink-muted">{column.label}</dt>
                        <dd>{column.hint}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </>
      )}
    </section>
  );
}
