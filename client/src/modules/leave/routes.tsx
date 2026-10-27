import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeaveOverviewPage = lazy(() => import("./pages/LeaveOverviewPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <LeaveOverviewPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "my-requests", element: <MyLeavesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "balances", element: <BalancesPage /> },
];
