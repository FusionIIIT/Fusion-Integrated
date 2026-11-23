import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const SubmitApplicationPage = lazy(() => import("./pages/SubmitApplicationPage"));
const ApplicationQueuePage = lazy(() => import("./pages/ApplicationQueuePage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const FilingsPage = lazy(() => import("./pages/FilingsPage"));
const OfficeActionsPage = lazy(() => import("./pages/OfficeActionsPage"));
const MaintenancePage = lazy(() => import("./pages/MaintenancePage"));
const LicensingPage = lazy(() => import("./pages/LicensingPage"));
const WorkflowPage = lazy(() => import("./pages/WorkflowPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <RequirePermission permission="pms.application.view_self"><MyApplicationsPage /></RequirePermission> },
  { path: "submit", element: <RequirePermission permission="pms.application.create"><SubmitApplicationPage /></RequirePermission> },
  { path: "queue", element: <RequirePermission permission="pms.application.view"><ApplicationQueuePage /></RequirePermission> },
  { path: "reviews", element: office("pms.application.review", <ReviewsPage />) },
  { path: "filings", element: office("pms.filing.record", <FilingsPage />) },
  { path: "office-actions", element: office("pms.office_action.record", <OfficeActionsPage />) },
  { path: "maintenance", element: office("pms.maintenance.manage", <MaintenancePage />) },
  { path: "licensing", element: office("pms.licensing.submit", <LicensingPage />) },
  { path: "oversight", element: office("pms.workflow.monitor", <WorkflowPage />) },
  { path: "reports", element: <RequirePermission permission="pms.report.view"><ReportsPage /></RequirePermission> },
  { path: "my-reports", element: <RequirePermission permission="pms.report.view_self"><ReportsPage personal /></RequirePermission> },
  { path: "admin", element: office("pms.config.manage", <AdminPage />) },
  { path: "audit", element: <RequirePermission permission="pms.audit.view"><AuditPage /></RequirePermission> },
];
