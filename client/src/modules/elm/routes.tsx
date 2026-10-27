import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** Lazy loaded route chunks for the ELM module. */
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const AdminLeavePage = lazy(() => import("./pages/AdminLeavePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
  { path: "admin", element: <AdminLeavePage /> },
];
