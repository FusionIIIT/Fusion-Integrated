import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const ProposalsListPage = lazy(() => import("./pages/ProposalsListPage"));
const ProjectsListPage = lazy(() => import("./pages/ProjectsListPage"));
const FinanceLedgerPage = lazy(() => import("./pages/FinanceLedgerPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="proposals" replace /> },
  { path: "proposals", element: guarded("rspc.proposal.view", <ProposalsListPage />) },
  { path: "projects", element: guarded("rspc.project.view", <ProjectsListPage />) },
  { path: "finance", element: guarded("rspc.fund.view", <FinanceLedgerPage />) },
];
