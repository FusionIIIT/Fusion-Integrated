import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const NewApplicationPage = lazy(() => import("./pages/NewApplicationPage"));
const PriorArtPage = lazy(() => import("./pages/PriorArtPage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const BudgetApprovalsPage = lazy(() => import("./pages/BudgetApprovalsPage"));
const MaintenanceDecisionsPage = lazy(() => import("./pages/MaintenanceDecisionsPage"));
const AttorneyDocketPage = lazy(() => import("./pages/AttorneyDocketPage"));
const OfficeActionsPage = lazy(() => import("./pages/OfficeActionsPage"));
const AllApplicationsPage = lazy(() => import("./pages/AllApplicationsPage"));
const AttorneyPanelPage = lazy(() => import("./pages/AttorneyPanelPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "new", element: <NewApplicationPage /> },
  { path: "prior-art", element: <PriorArtPage /> },
  { path: "reviews", element: office("patents.application.review", <ReviewsPage />) },
  { path: "budget-approvals", element: office("patents.budget.approve", <BudgetApprovalsPage />) },
  { path: "maintenance-decisions", element: office("patents.maintenance.decide", <MaintenanceDecisionsPage />) },
  { path: "docket", element: office("patents.assessment.perform", <AttorneyDocketPage />) },
  { path: "office-actions", element: office("patents.office_action.respond", <OfficeActionsPage />) },
  { path: "all", element: office("patents.application.view", <AllApplicationsPage />) },
  { path: "attorney-panel", element: office("patents.panel.manage", <AttorneyPanelPage />) },
  { path: "reports", element: office("patents.report.view", <ReportsPage />) },
];
