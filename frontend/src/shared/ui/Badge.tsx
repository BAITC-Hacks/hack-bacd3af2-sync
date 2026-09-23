import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-line bg-white/[0.04] text-ink-muted",
        accent: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
        good: "border-status-good/30 bg-status-good/10 text-ink",
        warning: "border-status-warning/30 bg-status-warning/10 text-ink",
        critical: "border-status-critical/40 bg-status-critical/10 text-ink",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
