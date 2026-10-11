import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
