import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const LeaveTasksPage = lazy(() => import("./pages/LeaveTasksPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "tasks", element: <LeaveTasksPage /> },
  { path: "balances", element: <BalancesPage /> },
];
