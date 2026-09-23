import { Link } from "@tanstack/react-router";

export function NotFound() {
  return (
    <div className="py-24 text-center">
      <p className="text-sm font-medium text-accent">404</p>
      <h1 className="mt-2 text-2xl font-semibold text-ink">Page not found</h1>
      <Link to="/forecast" className="mt-6 inline-block text-sm text-ink-muted hover:text-ink">
        Back to forecast →
      </Link>
    </div>
  );
}
