import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const ProposalsPage = lazy(() => import("./pages/ProposalsPage"));
const ConsultancyPage = lazy(() => import("./pages/ConsultancyPage"));
const FinancialPage = lazy(() => import("./pages/FinancialPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

/** Paths are RELATIVE — the shell mounts them under basePath (/rspc).
 *
 *  Every entry here matches a nav item in modules/rspc/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="proposals" replace /> },
  { path: "proposals", element: guarded("rspc.proposal.view", <ProposalsPage />) },
  { path: "consultancy", element: guarded("rspc.consultancy.view", <ConsultancyPage />) },
  { path: "financial", element: guarded("rspc.financial.request", <FinancialPage />) },
  { path: "reports", element: guarded("rspc.report.submit", <ReportsPage />) },
];
