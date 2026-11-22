import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const ClaimsPage = lazy(() => import("./pages/ClaimsPage"));
const AppraisalsPage = lazy(() => import("./pages/AppraisalsPage"));
const AdministrationPage = lazy(
  () => import("./pages/AdministrationPage"));
const NotificationsPage = lazy(
  () => import("./pages/NotificationsPage"));
const LeavesPage = lazy(() => import("./pages/LeavesPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="records" replace /> },
  { path: "records",
    element: office("hr.employee.view_self", <RecordsPage />) },
  { path: "employees",
    element: office("hr.employee.view", <RecordsPage />) },
  { path: "claims",
    element: office("hr.claim.view_self", <ClaimsPage />) },
  { path: "claims/queue",
    element: office("hr.claim.view", <ClaimsPage />) },
  { path: "claims/approvals",
    element: office("hr.claim.approve", <ClaimsPage />) },
  { path: "claims/processing",
    element: office("hr.claim.manage", <ClaimsPage />) },
  { path: "appraisals",
    element: office("hr.appraisal.view_self", <AppraisalsPage />) },
  { path: "appraisals/assignment",
    element: office("hr.appraisal.assign", <AppraisalsPage />) },
  { path: "appraisals/reviews",
    element: office("hr.appraisal.review", <AppraisalsPage />) },
  { path: "administration",
    element: office("hr.employee.view", <AdministrationPage />) },
  { path: "notifications",
    element: office("hr.notification.view", <NotificationsPage />) },
  { path: "leaves",
    element: office("hr.leave.view_self", <LeavesPage />) },
  { path: "leaves/queue",
    element: office("hr.leave.view", <LeavesPage />) },
  { path: "leaves/approvals",
    element: office("hr.leave.approve", <LeavesPage />) },
  { path: "leave-balances",
    element: office("hr.leave_balance.manage", <AdministrationPage />) },
];
