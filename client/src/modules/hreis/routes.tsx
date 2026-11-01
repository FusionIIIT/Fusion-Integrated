import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

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

/** Paths are RELATIVE — the shell mounts them under basePath "/hr". */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="overview" replace /> },
  { path: "overview", element: <OverviewPage /> },
  { path: "service-record", element: <ServiceRecordPage /> },
  { path: "leaves", element: <LeavesPage /> },
  { path: "appraisals", element: <AppraisalsPage /> },
  { path: "ltc", element: <LtcPage /> },
  { path: "cpda", element: <CpdaPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "verification", element: <VerificationQueuePage /> },
  { path: "appraisal-admin", element: <AppraisalAdminPage /> },
  { path: "admin", element: <AdminSettingsPage /> },
  { path: "audit", element: <AuditLogsPage /> },
  { path: "notifications", element: <NotificationsPage /> },
  { path: "settlement", element: <SettlementQueuePage /> },
];
