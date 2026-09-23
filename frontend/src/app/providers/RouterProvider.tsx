import { RouterProvider as TanStackRouterProvider } from "@tanstack/react-router";

import { router } from "../router/router";

export function RouterProvider() {
  return <TanStackRouterProvider router={router} />;
}
