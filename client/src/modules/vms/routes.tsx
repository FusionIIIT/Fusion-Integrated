import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const VisitsPage = lazy(() => import("./pages/VisitsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const GatePage = lazy(() => import("./pages/GatePage"));
const SecurityAlertsPage = lazy(() => import("./pages/SecurityAlertsPage"));
const MusterPage = lazy(() => import("./pages/MusterPage"));

function guard(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="visits" replace /> },
  { path: "visits", element: <VisitsPage /> },
  { path: "approvals", element: guard("vms.visit.approve", <ApprovalsPage />) },
  { path: "gate", element: guard("vms.gate.scan", <GatePage />) },
  { path: "security", element: guard("vms.security.admin", <SecurityAlertsPage />) },
  { path: "muster", element: guard("vms.emergency.muster", <MusterPage />) },
];
