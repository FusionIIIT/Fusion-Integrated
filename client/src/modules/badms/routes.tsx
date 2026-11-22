import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { RequirePermission } from "../../auth/RequirePermission";

const BackupsPage = lazy(() => import("./pages/BackupsPage"));
const SchedulesPage = lazy(() => import("./pages/SchedulesPage"));
const ArchivalRequestsPage = lazy(() => import("./pages/ArchivalRequestsPage"));
const StorageExtensionsPage = lazy(() => import("./pages/StorageExtensionsPage"));
const RestorationsPage = lazy(() => import("./pages/RestorationsPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const SecurityPoliciesPage = lazy(() => import("./pages/SecurityPoliciesPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

function BadmsIndex() {
  const { can } = useAuth();
  if (can("badms.backup.view")) {
    return <Navigate to="backups" replace />;
  }
  return <Navigate to="archival-requests" replace />;
}

export const routes: RouteObject[] = [
  { index: true, element: <BadmsIndex /> },
  { path: "backups", element: guarded("badms.backup.view", <BackupsPage />) },
  { path: "schedules", element: guarded("badms.backup.view", <SchedulesPage />) },
  { path: "archival-requests", element: guarded("badms.archival.view", <ArchivalRequestsPage />) },
  { path: "storage-extensions", element: guarded("badms.storage.view", <StorageExtensionsPage />) },
  { path: "restorations", element: guarded("badms.restoration.view", <RestorationsPage />) },
  { path: "audit-logs", element: guarded("badms.audit.view", <AuditLogsPage />) },
  { path: "reports", element: guarded("badms.report.view", <ReportsPage />) },
  { path: "security-policies", element: guarded("badms.security.manage", <SecurityPoliciesPage />) },
];
