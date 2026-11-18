import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const LeaveQueuePage = lazy(() => import("./pages/LeaveQueuePage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const ResumptionQueuePage = lazy(() => import("./pages/ResumptionQueuePage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));
export const routes: RouteObject[] = [
  { index: true, element: <MyLeavePage /> },
  { path: "queue", element: <LeaveQueuePage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
  { path: "resumptions", element: <ResumptionQueuePage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
