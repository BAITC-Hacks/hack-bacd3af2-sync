import { Wind } from "lucide-react";

export function Logo() {
  return (
    <span className="flex items-center gap-2.5">
      <span className="grid size-8 place-items-center rounded-lg bg-gradient-to-br from-cyan-400 to-violet-500 text-slate-950 shadow-[0_0_24px_-4px_rgb(34_211_238/0.7)]">
        <Wind className="size-4.5" strokeWidth={2.4} aria-hidden />
      </span>
      <span className="text-[15px] font-semibold tracking-tight text-ink">
        Wind<span className="text-accent">AI</span>
      </span>
    </span>
  );
}
