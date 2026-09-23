import { cn } from "@/shared/lib";

/** Thin-line three-blade turbine mark used as the WindAI logo. */
export function TurbineMark({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 40 48" fill="none" className={cn("text-cream", className)}>
      <g stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
        <path d="M20 16 L19.2 46 M20 16 L20.8 46" />
        <path d="M20 16 C19 11 19 6 20.2 1 C21 6 21.2 11 20 16" />
        <path d="M20 16 C24 18.5 29 21 34.5 22 C30.5 18.6 25.5 16.2 20 16" />
        <path d="M20 16 C16 18.5 11 21.5 5.5 22.6 C9.5 19 14.5 16.4 20 16" />
      </g>
      <circle cx="20" cy="16" r="1.6" fill="currentColor" />
    </svg>
  );
}
