import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const SubstitutePage = lazy(() => import("./pages/SubstitutePage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "substitutes", element: <SubstitutePage /> },
  { path: "balances", element: <BalancesPage /> },
];
