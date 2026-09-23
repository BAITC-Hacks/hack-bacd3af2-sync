import { cn } from "@/shared/lib";

type SeriesMarkerProps = {
  color: string;
  /** Filled dot or hollow ring — the shape carries identity together with the color. */
  shape: "dot" | "ring";
  className?: string;
};

export function SeriesMarker({ color, shape, className }: SeriesMarkerProps) {
  return (
    <span
      aria-hidden
      className={cn("inline-block size-2.5 shrink-0 rounded-full", className)}
      style={shape === "dot" ? { backgroundColor: color } : { boxShadow: `inset 0 0 0 2px ${color}` }}
    />
  );
}
