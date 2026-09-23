import { cva, type VariantProps } from "class-variance-authority";
import type { HTMLAttributes } from "react";

import { cn } from "@/shared/lib";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-[3px] text-[11.5px] font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-line bg-panel-soft text-ink-muted",
        accent: "border-cream/25 bg-cream/[0.07] text-cream",
        good: "border-sage/25 bg-sage/[0.09] text-sage",
        warning: "border-gold/30 bg-gold/[0.08] text-gold",
        critical: "border-status-critical/35 bg-status-critical/10 text-[#d99a8b]",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>;

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
