import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeavePage = lazy(() => import("./LeavePage"));
export const routes: RouteObject[] = [
  { path: "", element: <LeavePage /> },
  { path: "review", element: <LeavePage /> },
];
