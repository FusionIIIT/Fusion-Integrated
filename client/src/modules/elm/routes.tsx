import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const LeaveBalancePage = lazy(() => import("./pages/LeaveBalancePage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const LeaveTypesPage = lazy(() => import("./pages/LeaveTypesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "balance", element: <LeaveBalancePage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "types", element: <LeaveTypesPage /> },
];
