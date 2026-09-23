import { Outlet } from "@tanstack/react-router";

import { MobileHeader } from "@/widgets/header";
import { Sidebar } from "@/widgets/sidebar";

export function RootLayout() {
  return (
    <div className="flex min-h-dvh bg-canvas">
      <Sidebar />
      <div className="min-w-0 flex-1">
        <MobileHeader />
        <main className="px-4 pb-8 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
