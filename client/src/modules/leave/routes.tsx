import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

/** One lazy chunk per page. */
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const SubstitutePage = lazy(() => import("./pages/SubstitutePage"));
const ReviewQueuePage = lazy(() => import("./pages/ReviewQueuePage"));
const RoutingQueuePage = lazy(() => import("./pages/RoutingQueuePage"));
const SanctionQueuePage = lazy(() => import("./pages/SanctionQueuePage"));
const ResumptionsPage = lazy(() => import("./pages/ResumptionsPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath. */
export const routes: RouteObject[] = [
  { index: true, element: <MyLeavePage /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "substitute", element: <SubstitutePage /> },
  { path: "review", element: <ReviewQueuePage /> },
  { path: "routing", element: <RoutingQueuePage /> },
  { path: "sanction", element: <SanctionQueuePage /> },
  { path: "resumptions", element: <ResumptionsPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "policy", element: <PolicyPage /> },
];
