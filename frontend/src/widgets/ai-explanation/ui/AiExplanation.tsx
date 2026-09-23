import { Sparkles } from "lucide-react";
import { motion } from "motion/react";

import { WEATHER_SOURCE_LABELS, type ForecastResponse } from "@/entities/forecast";
import { baseTransition } from "@/shared/config";
import { formatRelativeTime } from "@/shared/lib";
import { Badge, Card, CardHeader, Skeleton } from "@/shared/ui";

import { WarningList } from "./WarningList";

type AiExplanationProps = {
  forecast: ForecastResponse | undefined;
  isLoading: boolean;
};

/** Split on sentence-ending punctuation followed by whitespace, so decimals like "0.98" stay intact. */
function splitSentences(text: string): string[] {
  return text.split(/(?<=[.!?])\s+/).filter(Boolean);
}

export function AiExplanation({ forecast, isLoading }: AiExplanationProps) {
  const sentences = forecast ? splitSentences(forecast.explanation) : [];

  return (
    <Card aria-labelledby="explanation-title">
      <CardHeader
        titleId="explanation-title"
        title="AI explanation"
        description="What the agent concluded from this run"
        icon={<Sparkles className="size-4" aria-hidden />}
        action={
          forecast?.warnings.length ? (
            <Badge tone="warning">{forecast.warnings.length} warning(s)</Badge>
          ) : null
        }
      />

      {isLoading ? (
        <div className="space-y-2.5">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-4/6" />
        </div>
      ) : forecast ? (
        <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
          <p key={forecast.generatedAt} className="text-[15px] leading-7 text-ink">
            {sentences.map((sentence, index) => (
              <motion.span
                key={`${index}-${sentence}`}
                initial={{ opacity: 0, filter: "blur(4px)" }}
                animate={{ opacity: 1, filter: "blur(0px)" }}
                transition={{ ...baseTransition, delay: 0.15 + index * 0.18 }}
              >
                {sentence}{" "}
              </motion.span>
            ))}
          </p>
          <div className="space-y-4">
            <WarningList warnings={forecast.warnings} />
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 border-t border-line pt-4 text-xs">
              <dt className="text-ink-subtle">Model</dt>
              <dd className="font-mono text-ink-muted">{forecast.modelVersion ?? "—"}</dd>
              <dt className="text-ink-subtle">Weather</dt>
              <dd className="text-ink-muted">
                {forecast.weatherSource ? (WEATHER_SOURCE_LABELS[forecast.weatherSource] ?? forecast.weatherSource) : "—"}
              </dd>
              <dt className="text-ink-subtle">Generated</dt>
              <dd className="text-ink-muted">{formatRelativeTime(forecast.generatedAt)}</dd>
            </dl>
          </div>
        </div>
      ) : (
        <motion.p
          className="text-sm text-ink-muted"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={baseTransition}
        >
          After the run, the agent summarises expected generation, links it to wind conditions, highlights
          low-output windows and flags operational anomalies.
        </motion.p>
      )}
    </Card>
  );
}
