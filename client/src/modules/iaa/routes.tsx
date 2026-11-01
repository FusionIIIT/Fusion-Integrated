import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const IaaWorkspace = lazy(() => import("./pages/IaaWorkspace"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <IaaWorkspace /> },
  { path: "finance", element: <IaaWorkspace /> },
  { path: "approvals", element: <IaaWorkspace /> },
  { path: "ta", element: <IaaWorkspace /> },
  { path: "anomalies", element: <IaaWorkspace /> },
  { path: "audit-observations", element: <IaaWorkspace /> },
  { path: "reports", element: <IaaWorkspace /> },
  { path: "notifications", element: <IaaWorkspace /> },
  { path: "configuration", element: <IaaWorkspace /> },
];
