import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveDashboardPage = lazy(() => import("./pages/LeaveDashboardPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <LeaveDashboardPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
