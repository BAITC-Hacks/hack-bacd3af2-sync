import { Sparkles } from "lucide-react";

import { Button } from "@/shared/ui";

type RunForecastButtonProps = {
  onRun: () => void;
  isRunning: boolean;
  className?: string;
};

export function RunForecastButton({ onRun, isRunning, className }: RunForecastButtonProps) {
  return (
    <Button
      size="lg"
      onClick={onRun}
      isLoading={isRunning}
      loadingText="Agent running…"
      icon={<Sparkles className="size-4" aria-hidden />}
      className={className}
    >
      Run AI Agent
    </Button>
  );
}
