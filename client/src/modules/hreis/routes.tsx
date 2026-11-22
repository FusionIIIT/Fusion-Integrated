import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyRecordPage = lazy(() => import("./pages/MyRecordPage"));
const RequestsPage = lazy(() => import("./pages/RequestsPage"));
const AdministrationPage = lazy(() => import("./pages/AdministrationPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));

function protectedPage(permission: string, content: ReactNode) {
  return <RequirePermission permission={permission}>{content}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-record" replace /> },
  { path: "my-record",
    element: protectedPage("hreis.service_record.view", <MyRecordPage />) },
  { path: "requests",
    element: protectedPage("hreis.request.view", <RequestsPage />) },
  { path: "leave",
    element: protectedPage("hreis.leave.create", <RequestsPage view="leave" />) },
  { path: "claims",
    element: protectedPage("hreis.claim.create", <RequestsPage view="claims" />) },
  { path: "appraisals",
    element: protectedPage("hreis.appraisal.create", <RequestsPage view="appraisal" />) },
  { path: "approvals",
    element: protectedPage("hreis.approval.view", <RequestsPage view="approvals" />) },
  { path: "finance",
    element: protectedPage("hreis.finance.review", <RequestsPage view="finance" />) },
  { path: "administration",
    element: protectedPage("hreis.service_record.update", <AdministrationPage />) },
  { path: "notifications",
    element: protectedPage("hreis.notification.view", <NotificationsPage />) },
  { path: "audit",
    element: protectedPage("hreis.audit.view", <AuditPage />) },
];
