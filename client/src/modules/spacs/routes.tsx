import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const OpportunitiesPage = lazy(() => import("./pages/OpportunitiesPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const VerificationQueuePage = lazy(() => import("./pages/VerificationQueuePage"));
const DecisionsPage = lazy(() => import("./pages/DecisionsPage"));
const ConvocationAwardsPage = lazy(() => import("./pages/ConvocationAwardsPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="catalogue" replace /> },
  { path: "catalogue", element: <OpportunitiesPage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "verification", element: office("spacs.application.review", <VerificationQueuePage />) },
  { path: "decisions", element: office("spacs.application.approve", <DecisionsPage />) },
  { path: "awards", element: office("spacs.award.publish", <ConvocationAwardsPage />) },
];
