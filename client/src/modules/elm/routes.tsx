import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveDashboardPage = lazy(() => import("./pages/LeaveDashboardPage"));
const LeaveApplyPage = lazy(() => import("./pages/LeaveApplyPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <LeaveDashboardPage /> },
  { path: "apply", element: <LeaveApplyPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "calendar", element: <HolidayCalendarPage /> },
];
