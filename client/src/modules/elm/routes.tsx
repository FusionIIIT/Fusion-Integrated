import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
];
