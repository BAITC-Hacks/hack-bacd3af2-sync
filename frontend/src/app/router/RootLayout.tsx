import { Outlet } from "@tanstack/react-router";

import { Header } from "@/widgets/header";

function Backdrop() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_20%_-10%,rgb(34_211_238/0.16),transparent_60%),radial-gradient(ellipse_60%_50%_at_90%_0%,rgb(139_92_246/0.16),transparent_60%),radial-gradient(ellipse_70%_60%_at_50%_110%,rgb(59_130_246/0.10),transparent_60%)]" />
      <div className="bg-grid absolute inset-0 [mask-image:radial-gradient(ellipse_70%_55%_at_50%_0%,#000_30%,transparent_75%)]" />
    </div>
  );
}

export function RootLayout() {
  return (
    <div className="relative isolate min-h-dvh">
      <Backdrop />
      <Header />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <footer className="mx-auto max-w-7xl border-t border-line px-4 py-6 text-xs text-ink-subtle sm:px-6 lg:px-8">
        WindAI · Agentic AI for wind farm power forecasting
      </footer>
    </div>
  );
}
