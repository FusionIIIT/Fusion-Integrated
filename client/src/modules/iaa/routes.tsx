import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyRequestsPage = lazy(() => import("./pages/MyRequestsPage"));
const FinanceReviewPage = lazy(() => import("./pages/FinanceReviewPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AnomaliesPage = lazy(() => import("./pages/AnomaliesPage"));
const ObservationsPage = lazy(() => import("./pages/ObservationsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const ConfigurationPage = lazy(() => import("./pages/ConfigurationPage"));

// Each page is closed to the roles its nav item's required_permission excludes (registry.py).
function guard(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="notifications" replace /> },
  { path: "my-requests", element: guard("iaa.request.create", <MyRequestsPage />) },
  { path: "finance", element: guard("iaa.request.review", <FinanceReviewPage />) },
  { path: "approvals", element: guard("iaa.request.approve", <ApprovalsPage />) },
  { path: "anomalies", element: guard("iaa.anomaly.view", <AnomaliesPage />) },
  { path: "observations", element: guard("iaa.observation.view", <ObservationsPage />) },
  { path: "reports", element: guard("iaa.report.view", <ReportsPage />) },
  { path: "notifications", element: guard("iaa.notification.view", <NotificationsPage />) },
  { path: "configuration", element: guard("iaa.configuration.view", <ConfigurationPage />) },
];
