import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ProposalsPage = lazy(() => import("./pages/ProposalsPage"));
const ConsultancyPage = lazy(() => import("./pages/ConsultancyPage"));
const FinancialPage = lazy(() => import("./pages/FinancialPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

/** Paths are RELATIVE — the shell mounts them under basePath (/rspc).
 *
 *  Every entry here matches a nav item in modules/rspc/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="proposals" replace /> },
  { path: "proposals", element: <ProposalsPage /> },
  { path: "consultancy", element: <ConsultancyPage /> },
  { path: "financial", element: <FinancialPage /> },
  { path: "reports", element: <ReportsPage /> },
];
