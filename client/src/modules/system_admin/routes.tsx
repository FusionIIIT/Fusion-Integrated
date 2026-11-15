import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const ArchivalPage = lazy(() => import("./pages/ArchivalPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath (/admin).
 *
 *  Every entry here has a matching nav item in the server's registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "users", element: <UsersPage /> },
  { path: "roles", element: <RolesPage /> },
  { path: "archival", element: <ArchivalPage /> },
  { path: "audit", element: <AuditLogsPage /> },
  { path: "settings", element: <SettingsPage /> },
];
