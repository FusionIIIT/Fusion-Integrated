import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const Dashboard = lazy(() => import("./pages/LeaveDashboardPage"));
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <Dashboard /> },
  { path: "apply", element: <Dashboard /> },
];
