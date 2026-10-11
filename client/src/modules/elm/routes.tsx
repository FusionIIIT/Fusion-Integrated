import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "history", element: <MyApplicationsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
];
