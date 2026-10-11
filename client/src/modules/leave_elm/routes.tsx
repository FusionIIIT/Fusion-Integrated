import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const LeaveHistoryPage = lazy(() => import("./pages/LeaveHistoryPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "history", element: <LeaveHistoryPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
];
