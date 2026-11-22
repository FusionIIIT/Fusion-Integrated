import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeaveDashboardPage = lazy(() => import("./pages/LeaveDashboardPage"));
const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));
const LeaveReviewPage = lazy(() => import("./pages/LeaveReviewPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <LeaveDashboardPage /> },
  { path: "requests", element: <LeaveRequestsPage /> },
  { path: "review", element: <LeaveReviewPage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
];
