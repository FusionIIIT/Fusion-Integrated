import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const ArchivePage = lazy(() => import("./pages/ArchivePage"));
const PurgePage = lazy(() => import("./pages/PurgePage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const SystemPolicyPage = lazy(() => import("./pages/SystemPolicyPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: guarded("superadmin.user.view", <DashboardPage />) },
  { path: "users", element: guarded("superadmin.user.view", <UsersPage />) },
  { path: "roles", element: guarded("superadmin.role.view", <RolesPage />) },
  { path: "archive", element: guarded("superadmin.archive.view", <ArchivePage />) },
  { path: "purge", element: guarded("superadmin.purge.approve", <PurgePage />) },
  { path: "audit", element: guarded("superadmin.audit_log.view", <AuditPage />) },
  { path: "config", element: guarded("superadmin.system_config.view", <SystemPolicyPage />) },
];
