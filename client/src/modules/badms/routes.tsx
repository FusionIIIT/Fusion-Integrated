import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const BackupsPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).BackupsPage,
}));
const SchedulesPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).SchedulesPage,
}));
const ArchivesPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).ArchivesPage,
}));
const RestoresPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).RestoresPage,
}));
const StorageExtensionsPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).StorageExtensionsPage,
}));
const AuditPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).AuditPage,
}));
const ReportsPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).ReportsPage,
}));
const SecurityPoliciesPage = lazy(async () => ({
  default: (await import("./pages/BadmsPages")).SecurityPoliciesPage,
}));

function page(permission: string, element: ReactNode) {
  return <RequirePermission permission={permission}>{element}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="backups" replace /> },
  { path: "backups", element: page("badms.backup.view", <BackupsPage />) },
  { path: "schedules", element: page("badms.schedule.view", <SchedulesPage />) },
  { path: "archives", element: page("badms.archive.view", <ArchivesPage />) },
  { path: "restores", element: page("badms.restore.view", <RestoresPage />) },
  {
    path: "storage-extensions",
    element: page("badms.storage_extension.view", <StorageExtensionsPage />),
  },
  { path: "audit", element: page("badms.audit_event.view", <AuditPage />) },
  { path: "reports", element: page("badms.report.view", <ReportsPage />) },
  {
    path: "security-policies",
    element: page("badms.security_policy.manage", <SecurityPoliciesPage />),
  },
];
