import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeaveHomePage = lazy(() => import("./pages/LeaveHomePage"));

export const routes: RouteObject[] = [
  { index: true, element: <LeaveHomePage /> },
];
