import { MotionConfig } from "motion/react";

import { QueryProvider } from "./QueryProvider";
import { RouterProvider } from "./RouterProvider";

export function AppProviders() {
  return (
    <MotionConfig reducedMotion="user">
      <QueryProvider>
        <RouterProvider />
      </QueryProvider>
    </MotionConfig>
  );
}
