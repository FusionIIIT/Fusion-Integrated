import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can split these cleanly. */
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const BulkUsersPage = lazy(() => import("./pages/BulkUsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const ArchivalPage = lazy(() => import("./pages/ArchivalPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const SystemConfigPage = lazy(() => import("./pages/SystemConfigPage"));

/** Paths are RELATIVE to the manifest's basePath (/sysadmin).
 * Every entry here has a matching nav item in modules/system_admin/registry.py.
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "users", element: <UsersPage /> },
  { path: "users/bulk", element: <BulkUsersPage /> },
  { path: "roles", element: <RolesPage /> },
  { path: "archival", element: <ArchivalPage /> },
  { path: "purge", element: <ArchivalPage /> },
  { path: "audit", element: <AuditLogsPage /> },
  { path: "config", element: <SystemConfigPage /> },
];
