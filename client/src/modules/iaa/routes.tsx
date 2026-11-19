import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const IaaWorkspace = lazy(() => import("./pages/IaaWorkspace"));

export const routes: RouteObject[] = [
  { index: true, element: <IaaWorkspace /> },
  { path: "expenses", element: <IaaWorkspace /> },
  { path: "ta", element: <IaaWorkspace /> },
  { path: "budgets", element: <IaaWorkspace /> },
  { path: "anomalies", element: <IaaWorkspace /> },
  { path: "audit", element: <IaaWorkspace /> },
];
