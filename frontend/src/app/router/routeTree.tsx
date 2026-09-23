import { createRootRoute, createRoute, redirect } from "@tanstack/react-router";

import { AboutPage } from "@/pages/about";
import { ForecastPage } from "@/pages/forecast";

import { NotFound } from "./NotFound";
import { RootLayout } from "./RootLayout";

const rootRoute = createRootRoute({
  component: RootLayout,
  notFoundComponent: NotFound,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/forecast" });
  },
});

const forecastRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/forecast",
  component: ForecastPage,
});

const aboutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/about",
  component: AboutPage,
});

export const routeTree = rootRoute.addChildren([indexRoute, forecastRoute, aboutRoute]);
