import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const RequestsPage = lazy(() => import("./pages/RequestsPage"));
const TravelClaimsPage = lazy(() => import("./pages/TravelClaimsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AnomaliesPage = lazy(() => import("./pages/AnomaliesPage"));
const AuditObservationsPage = lazy(() => import("./pages/AuditObservationsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const ConfigurationPage = lazy(() => import("./pages/ConfigurationPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <RequestsPage /> },
  { path: "travel", element: <TravelClaimsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "anomalies", element: <AnomaliesPage /> },
  { path: "audit", element: <AuditObservationsPage /> },
  { path: "reports", element: <ReportsPage /> },
  { path: "config", element: <ConfigurationPage /> },
];
