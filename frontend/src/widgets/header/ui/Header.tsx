import { Link } from "@tanstack/react-router";

import { ApiStatus } from "./ApiStatus";
import { Logo } from "./Logo";

const NAV_ITEMS = [
  { to: "/forecast", label: "Forecast" },
  { to: "/about", label: "How it works" },
] as const;

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/70 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <Link to="/forecast" aria-label="WindAI home">
          <Logo />
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-lg px-3 py-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
              activeProps={{ className: "bg-white/[0.06] text-ink" }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="hidden sm:block">
          <ApiStatus />
        </div>
      </div>
    </header>
  );
}
