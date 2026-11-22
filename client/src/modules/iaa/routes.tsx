import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import "./iaa.css";

const ExpenseRequestsPage = lazy(() => import("./pages/ExpenseRequestsPage"));
const TravelClaimsPage = lazy(() => import("./pages/TravelClaimsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const ConfigurationPage = lazy(() => import("./pages/ConfigurationPage"));
const AnomaliesPage = lazy(() => import("./pages/AnomaliesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="expenses" replace /> },
  { path: "expenses", element: <ExpenseRequestsPage /> },
  { path: "ta", element: <TravelClaimsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "audit", element: <AuditPage /> },
  { path: "reports", element: <ReportsPage /> },
  { path: "notifications", element: <NotificationsPage /> },
  { path: "configuration", element: <ConfigurationPage /> },
  { path: "anomalies", element: <AnomaliesPage /> },
];
