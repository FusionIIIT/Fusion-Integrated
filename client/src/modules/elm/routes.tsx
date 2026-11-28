import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const LeaveDashboard = lazy(() => import("./LeaveDashboard"));

export const routes: RouteObject[] = [
  { index: true, element: <LeaveDashboard /> },
  { path: "dashboard", element: <LeaveDashboard /> },
];
