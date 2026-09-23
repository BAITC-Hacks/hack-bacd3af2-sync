import { toForecastRequest, useRunForecast } from "@/entities/forecast";
import { Reveal } from "@/shared/ui";
import { AgentActivity } from "@/widgets/agent-activity";
import { AiExplanation } from "@/widgets/ai-explanation";
import { PowerForecastChart } from "@/widgets/forecast-chart";
import { ForecastControls } from "@/widgets/forecast-controls";
import { MetricsPanel } from "@/widgets/metrics-panel";
import { ForecastSummaryCard } from "@/widgets/turbine-summary";
import { WeatherPanel } from "@/widgets/weather-panel";

import { useForecastParams } from "../model/useForecastParams";

export function ForecastPage() {
  const { params, updateParams } = useForecastParams();
  const runForecast = useRunForecast();

  const forecast = runForecast.data;
  const isRunning = runForecast.isPending;
  const handleRun = () => runForecast.mutate(toForecastRequest(params));

  return (
    <div className="pb-16">
      <ForecastControls params={params} onParamsChange={updateParams} onRun={handleRun} isRunning={isRunning} />

      <div className="mt-8 grid gap-5 lg:grid-cols-12">
        <Reveal className="lg:col-span-7" delay={0.2}>
          <ForecastSummaryCard forecast={forecast} isLoading={isRunning} />
        </Reveal>
        <Reveal className="lg:col-span-5" delay={0.28}>
          <AgentActivity forecast={forecast} isRunning={isRunning} error={runForecast.error} />
        </Reveal>

        <Reveal className="lg:col-span-12" delay={0.36}>
          <PowerForecastChart forecast={forecast} isLoading={isRunning} />
        </Reveal>

        <Reveal className="lg:col-span-7" delay={0.44}>
          <WeatherPanel forecast={forecast} isLoading={isRunning} />
        </Reveal>
        <Reveal className="lg:col-span-5" delay={0.5}>
          <MetricsPanel />
        </Reveal>

        <Reveal className="lg:col-span-12" delay={0.56}>
          <AiExplanation forecast={forecast} isLoading={isRunning} />
        </Reveal>
      </div>
    </div>
  );
}
