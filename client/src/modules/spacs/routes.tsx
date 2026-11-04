
import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const SpacsHomePage = lazy(
  () => import("./pages/SpacsHomePage")
);

export const routes: RouteObject[] = [
  {
    index: true,
    element: <SpacsHomePage />,
  },
  {
    path: "catalogue",
    element: <SpacsHomePage />,
  },
  {
    path: "mine",
    element: <SpacsHomePage />,
  },
  {
    path: "verification",
    element: <SpacsHomePage />,
  },
  {
    path: "decisions",
    element: <SpacsHomePage />,
  },
  {
    path: "awards",
    element: <SpacsHomePage />,
  },
  {
    path: "evaluation",
    element: <SpacsHomePage />,
  },
  {
    path: "admin",
    element: <SpacsHomePage />,
  },
  {
    path: "audit",
    element: <SpacsHomePage />,
  },
];
