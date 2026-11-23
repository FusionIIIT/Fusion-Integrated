import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ArchivalPage = lazy(() => import("./pages/ArchivalPage"));
const PurgePage = lazy(() => import("./pages/PurgePage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: guarded("superadmin.dashboard.view", <DashboardPage />) },
  { path: "archival", element: guarded("superadmin.archival.view", <ArchivalPage />) },
  { path: "purge", element: guarded("superadmin.purge.view", <PurgePage />) },
  { path: "policy", element: guarded("superadmin.policy.view", <PolicyPage />) },
  { path: "audit", element: guarded("superadmin.audit.view", <AuditPage />) },
];
