import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const StandingInPage = lazy(() => import("./pages/StandingInPage"));
const ReviewQueuePage = lazy(() => import("./pages/ReviewQueuePage"));
const RoutingQueuePage = lazy(() => import("./pages/RoutingQueuePage"));
const SanctionQueuePage = lazy(() => import("./pages/SanctionQueuePage"));
const ResumptionsPage = lazy(() => import("./pages/ResumptionsPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "substitute", element: <StandingInPage /> },
  { path: "review", element: <ReviewQueuePage /> },
  { path: "routing", element: <RoutingQueuePage /> },
  { path: "sanction", element: <SanctionQueuePage /> },
  { path: "resumptions", element: <ResumptionsPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "policy", element: <PolicyPage /> },
];
