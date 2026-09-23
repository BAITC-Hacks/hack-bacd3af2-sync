import { Info, Target } from "lucide-react";
import { motion } from "motion/react";

import { useModelMetrics, type ModelMetrics, type ModelMetricsReport } from "@/entities/metrics";
import { TURBINES } from "@/entities/turbine";
import { EASE_OUT_EXPO } from "@/shared/config";
import { formatShortDate } from "@/shared/lib";
import { Badge, Card, CardHeader, Skeleton } from "@/shared/ui";

const COLUMNS = [
  { key: "mae", label: "MAE", hint: "Mean absolute error — lower is better" },
  { key: "rmse", label: "RMSE", hint: "Root mean squared error — lower is better" },
  { key: "r2", label: "R²", hint: "Explained variance — closer to 1 is better" },
] as const satisfies readonly { key: keyof Omit<ModelMetrics, "turbineId">; label: string; hint: string }[];

function describeSource(report: ModelMetricsReport | undefined): string {
  if (!report) return "Model quality per turbine";
  if (report.source === "demo" || !report.evaluation) return "Placeholder values — mock model is serving";
  const { periodStart, periodEnd } = report.evaluation;
  return `Hold-out ${formatShortDate(periodStart)} – ${formatShortDate(periodEnd)}`;
}

function MetricsRow({ model, index }: { model: ModelMetrics; index: number }) {
  const turbine = TURBINES[model.turbineId];
  return (
    <tr className="border-t border-line">
      <th scope="row" className="py-3.5 pr-3 text-left font-medium text-ink">
        <span className="flex items-center gap-2">
          <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: turbine.color }} />
          {turbine.name}
        </span>
        {model.n !== null ? (
          <span className="mt-0.5 block text-[11px] font-normal text-ink-subtle tabular-nums">
            n = {model.n.toLocaleString("en-US")}
          </span>
        ) : null}
      </th>
      {COLUMNS.map((column) => (
        <td key={column.key} className="px-2 py-3.5 text-right text-ink tabular-nums">
          {model[column.key].toFixed(3)}
        </td>
      ))}
      <td className="w-24 py-3.5 pl-3" aria-hidden>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.05]">
          <motion.div
            className="h-full rounded-full"
            style={{ backgroundColor: turbine.color }}
            initial={{ width: 0 }}
            animate={{ width: `${Math.max(0, model.r2) * 100}%` }}
            transition={{ duration: 1, delay: 0.2 + index * 0.1, ease: EASE_OUT_EXPO }}
          />
        </div>
      </td>
    </tr>
  );
}

export function MetricsPanel() {
  const { data, isPending, isError, error } = useModelMetrics();

  return (
    <Card className="h-full" aria-labelledby="metrics-title">
      <CardHeader
        titleId="metrics-title"
        title="Model metrics"
        description={describeSource(data)}
        icon={<Target className="size-4" aria-hidden />}
        action={
          data ? (
            <Badge tone={data.source === "holdout" ? "accent" : "neutral"}>
              {data.source === "holdout" ? "Holdout · observed weather" : "Demo metrics"}
            </Badge>
          ) : null
        }
      />

      {isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
          <Skeleton className="h-10" />
        </div>
      ) : isError ? (
        <p role="alert" className="text-sm text-ink-muted">
          Metrics unavailable: {error.message}
        </p>
      ) : (
        <>
          <table className="w-full text-sm">
            <caption className="sr-only">Model error metrics per turbine</caption>
            <thead>
              <tr className="text-xs text-ink-subtle">
                <th scope="col" className="pb-2 text-left font-medium">
                  Turbine
                </th>
                {COLUMNS.map((column) => (
                  <th key={column.key} scope="col" title={column.hint} className="px-2 pb-2 text-right font-medium">
                    {column.label}
                  </th>
                ))}
                <th scope="col" className="pb-2 pl-3 text-left font-medium">
                  <span className="sr-only">R² bar</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {data.models.map((model, index) => (
                <MetricsRow key={model.turbineId} model={model} index={index} />
              ))}
            </tbody>
          </table>
          {data.evaluation ? (
            <p className="mt-4 flex gap-2 rounded-xl border border-line bg-white/[0.025] px-3 py-2.5 text-xs leading-relaxed text-ink-muted">
              <Info className="mt-0.5 size-3.5 shrink-0 text-ink-subtle" aria-hidden />
              <span>{data.evaluation.note}</span>
            </p>
          ) : null}
          <dl className="mt-5 grid gap-2 border-t border-line pt-4 text-xs text-ink-subtle">
            {COLUMNS.map((column) => (
              <div key={column.key} className="flex gap-2">
                <dt className="w-10 font-medium text-ink-muted">{column.label}</dt>
                <dd>{column.hint}</dd>
              </div>
            ))}
          </dl>
        </>
      )}
    </Card>
  );
}
