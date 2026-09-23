import { ShieldCheck, TriangleAlert } from "lucide-react";
import { motion } from "motion/react";

import { baseTransition } from "@/shared/config";

type WarningListProps = {
  warnings: string[];
};

export function WarningList({ warnings }: WarningListProps) {
  if (warnings.length === 0) {
    return (
      <p className="flex items-center gap-2 text-sm text-ink-muted">
        <ShieldCheck className="size-4 text-status-good" aria-hidden />
        No anomalies detected — all checks passed.
      </p>
    );
  }

  return (
    <ul className="space-y-2" aria-label="Warnings">
      {warnings.map((warning, index) => (
        <motion.li
          key={warning}
          className="flex gap-2.5 rounded-xl border border-status-warning/25 bg-status-warning/[0.06] px-3 py-2.5 text-sm text-ink"
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ ...baseTransition, delay: 0.3 + index * 0.08 }}
        >
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-status-warning" aria-hidden />
          <span>
            <span className="sr-only">Warning: </span>
            {warning}
          </span>
        </motion.li>
      ))}
    </ul>
  );
}
