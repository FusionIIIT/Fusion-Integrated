import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** Lazy-loaded ELM pages. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const LeaveApplicationPage = lazy(() => import("./pages/LeaveApplicationPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const PrintApplicationPage = lazy(() => import("./pages/PrintApplicationPage"));
const SLAConfigPage = lazy(() => import("./pages/SLAConfigPage"));
const YearEndProcessingPage = lazy(() => import("./pages/YearEndProcessingPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <LeaveApplicationPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "history", element: <HistoryPage /> },
  { path: "print", element: <PrintApplicationPage /> },
  { path: "sla/thresholds", element: <SLAConfigPage /> },
  { path: "year-end", element: <YearEndProcessingPage /> },
];