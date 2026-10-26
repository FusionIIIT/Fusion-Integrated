import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));
const LeavePoliciesPage = lazy(() => import("./pages/LeavePoliciesPage"));
const OfflineSanctionsPage = lazy(() => import("./pages/OfflineSanctionsPage"));

/** Paths are RELATIVE — mounted under /leave by the shell.
 *  Every entry matches a NAV_ITEM in modules/elm/registry.py.
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "balance", element: <LeaveBalancesPage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "calendar", element: <HolidayCalendarPage /> },
  { path: "types", element: <LeavePoliciesPage /> },
  { path: "offline-entry", element: <OfflineSanctionsPage /> },
];
