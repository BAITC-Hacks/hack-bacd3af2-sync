import { ArrowRight, Send } from "lucide-react";

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
      loadingText="Агент работает…"
      icon={<Send className="size-[18px]" strokeWidth={1.7} aria-hidden />}
      trailingIcon={<ArrowRight className="ml-3 size-[18px]" strokeWidth={1.5} aria-hidden />}
      className={className}
    >
      Запустить агента
    </Button>
  );
}
