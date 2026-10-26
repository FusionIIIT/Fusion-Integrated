import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const SubmitLeavePage = lazy(() => import("./pages/SubmitLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my" replace /> },
  { path: "my", element: <MyLeavePage /> },
  { path: "submit", element: <SubmitLeavePage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
];
