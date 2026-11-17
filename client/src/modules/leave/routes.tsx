import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const LeaveHistoryPage = lazy(() => import("./pages/LeaveHistoryPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="balances" replace /> },
  { path: "balances", element: <LeaveBalancesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "history", element: <LeaveHistoryPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];

export default routes;
