import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/**
 * System Admin Module route definitions.
 * Code-split chunk per page component for fast lazy loading.
 */
const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const UserDetailPage = lazy(() => import("./pages/UserDetailPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const RoleAssignmentsPage = lazy(() => import("./pages/RoleAssignmentsPage"));
const ArchivalPage = lazy(() => import("./pages/ArchivalPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const AuditReportsPage = lazy(() => import("./pages/AuditReportsPage"));
const ConfigurationPage = lazy(() => import("./pages/ConfigurationPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "users", element: <UsersPage /> },
  { path: "users/:id", element: <UserDetailPage /> },
  { path: "roles", element: <RolesPage /> },
  { path: "assignments", element: <RoleAssignmentsPage /> },
  { path: "archival", element: <ArchivalPage /> },
  { path: "audit", element: <AuditLogsPage /> },
  { path: "reports", element: <AuditReportsPage /> },
  { path: "configuration", element: <ConfigurationPage /> },
];
