import { lazy, type ReactNode } from "react";
import type { RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const ArchivesPage = lazy(() => import("./pages/ArchivesPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const SystemConfigPage = lazy(() => import("./pages/SystemConfigPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: guarded("system_admin.user.view", <DashboardPage />) },
  { path: "", element: guarded("system_admin.user.view", <DashboardPage />) },
  { path: "users", element: guarded("system_admin.user.view", <UsersPage />) },
  { path: "roles", element: guarded("system_admin.role.view", <RolesPage />) },
  { path: "archives", element: guarded("system_admin.archive.view", <ArchivesPage />) },
  { path: "audit", element: guarded("system_admin.audit.view", <AuditLogsPage />) },
  { path: "config", element: guarded("system_admin.config.change", <SystemConfigPage />) },
];
