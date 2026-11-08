import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const FileDashboard = lazy(() => import("./FileDashboard"));

export const routes: RouteObject[] = [
  { index: true, element: <FileDashboard /> },
  { path: "files", element: <FileDashboard /> },
];