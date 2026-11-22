import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** Lazy load each page for code-splitting. */
const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const ServiceRecordPage = lazy(() => import("./pages/ServiceRecordPage"));
const LeavesPage = lazy(() => import("./pages/LeavesPage"));
const AppraisalsPage = lazy(() => import("./pages/AppraisalsPage"));
const LtcPage = lazy(() => import("./pages/LtcPage"));
const CpdaPage = lazy(() => import("./pages/CpdaPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const VerificationQueuePage = lazy(() => import("./pages/VerificationQueuePage"));
const AppraisalAdminPage = lazy(() => import("./pages/AppraisalAdminPage"));
const AdminSettingsPage = lazy(() => import("./pages/AdminSettingsPage"));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const SettlementQueuePage = lazy(() => import("./pages/SettlementQueuePage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

/** Paths are RELATIVE — the shell mounts them under basePath "/hr". */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="overview" replace /> },
  { path: "overview", element: <OverviewPage /> },
  { path: "service-record", element: <ServiceRecordPage /> },
  { path: "leaves", element: <LeavesPage /> },
  { path: "appraisals", element: <AppraisalsPage /> },
  { path: "ltc", element: <LtcPage /> },
  { path: "cpda", element: <CpdaPage /> },
  { path: "approvals", element: office("hr_eis.leave.review", <ApprovalsPage />) },
  { path: "verification", element: office("hr_eis.ltc.verify", <VerificationQueuePage />) },
  { path: "appraisal-admin", element: office("hr_eis.appraisal.assign_reviewer", <AppraisalAdminPage />) },
  { path: "admin", element: office("hr_eis.service_record.manage", <AdminSettingsPage />) },
  { path: "audit", element: office("hr_eis.audit.view", <AuditLogsPage />) },
  { path: "notifications", element: <NotificationsPage /> },
  { path: "settlement", element: office("hr_eis.ltc.settle", <SettlementQueuePage />) },
];
