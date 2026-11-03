import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const ApplicationDetailPage = lazy(() => import("./pages/ApplicationDetailPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "applications/new", element: <ApplicationDetailPage /> },
  { path: "applications/:appId", element: <ApplicationDetailPage /> },
  { path: "reports", element: <ReportsPage /> },
];
