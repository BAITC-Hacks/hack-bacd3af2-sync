import { cn } from "@/shared/lib";

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div aria-hidden className={cn("relative overflow-hidden rounded-lg bg-panel-soft", className)}>
      <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-cream/[0.05] to-transparent" />
    </div>
  );
}
