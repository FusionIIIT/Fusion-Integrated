import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const PassesPage = lazy(() => import("./pages/PassesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const GatePage = lazy(() => import("./pages/GatePage"));
const BlacklistPage = lazy(() => import("./pages/BlacklistPage"));
const EmergencyPage = lazy(() => import("./pages/EmergencyPage"));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="passes" replace /> },
  { path: "passes", element: <PassesPage /> },
  { path: "approvals", element: office("vms.visit.decide", <ApprovalsPage />) },
  { path: "gate", element: office("vms.gate.validate", <GatePage />) },
  { path: "blacklist", element: office("vms.blacklist.manage", <BlacklistPage />) },
  { path: "emergency", element: office("vms.emergency.trigger", <EmergencyPage />) },
  { path: "analytics", element: office("vms.analytics.view", <AnalyticsPage />) },
];
