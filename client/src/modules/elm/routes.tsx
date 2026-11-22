import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveDashboardPage = lazy(() => import("./pages/LeaveDashboardPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const UnitHeadApprovalsPage = lazy(() => import("./pages/UnitHeadApprovalsPage"));
const SanctioningQueuePage = lazy(() => import("./pages/SanctioningQueuePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <LeaveDashboardPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "substitute-requests", element: <SubstituteRequestsPage /> },
  { path: "unit-head-approvals", element: <UnitHeadApprovalsPage /> },
  { path: "sanctioning-queue", element: <SanctioningQueuePage /> },
];
