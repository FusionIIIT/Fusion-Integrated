import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));

export const routes: RouteObject[] = [
  { index: true, element: <DashboardPage /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "leave", element: <DashboardPage /> },
  { path: "bonafide", element: <DashboardPage /> },
  { path: "no-dues", element: <DashboardPage /> },
  { path: "assistantship", element: <DashboardPage /> },
  { path: "seminars", element: <DashboardPage /> },
  { path: "assignments", element: <DashboardPage /> },
];

export default routes;
