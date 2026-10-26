import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeaveRequestsPage = lazy(() => import("./pages/MyLeaveRequestsPage"));
const LeaveBalancePage = lazy(() => import("./pages/LeaveBalancePage"));
const LeaveHistoryPage = lazy(() => import("./pages/LeaveHistoryPage"));
const PendingApprovalsPage = lazy(() => import("./pages/PendingApprovalsPage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const LeavePolicyPage = lazy(() => import("./pages/LeavePolicyPage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));
const OfflineLeaveEntryPage = lazy(() => import("./pages/OfflineLeaveEntryPage"));
const LeaveReportsPage = lazy(() => import("./pages/LeaveReportsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "my-requests", element: <MyLeaveRequestsPage /> },
  { path: "balance", element: <LeaveBalancePage /> },
  { path: "history", element: <LeaveHistoryPage /> },
  {
    path: "pending-approvals",
    element: (
      <RequirePermission code="leave_management.leave_request.approve">
        <PendingApprovalsPage />
      </RequirePermission>
    ),
  },
  {
    path: "substitute-requests",
    element: (
      <RequirePermission code="leave_management.substitute_request.respond">
        <SubstituteRequestsPage />
      </RequirePermission>
    ),
  },
  {
    path: "policy",
    element: (
      <RequirePermission code="leave_management.leave_policy.manage">
        <LeavePolicyPage />
      </RequirePermission>
    ),
  },
  {
    path: "calendar",
    element: (
      <RequirePermission code="leave_management.holiday_calendar.manage">
        <HolidayCalendarPage />
      </RequirePermission>
    ),
  },
  {
    path: "offline-entry",
    element: (
      <RequirePermission code="leave_management.offline_leave.record">
        <OfflineLeaveEntryPage />
      </RequirePermission>
    ),
  },
  {
    path: "reports",
    element: (
      <RequirePermission code="leave_management.year_end.process">
        <LeaveReportsPage />
      </RequirePermission>
    ),
  },
];