import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeavePage = lazy(() => import("./pages/LeavePage"));

export const routes: RouteObject[] = [
  { index: true, element: <LeavePage /> },
];
