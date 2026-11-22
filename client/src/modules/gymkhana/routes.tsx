import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const ClubsPage = lazy(() => import("./pages/ClubsPage"));
const PollsPage = lazy(() => import("./pages/PollsPage"));
const ManagementPage = lazy(() => import("./pages/ManagementPage"));
const ActivityPage = lazy(() => import("./pages/ActivityPage"));
const MembershipsPage = lazy(() => import("./pages/MembershipsPage"));
const BudgetsPage = lazy(() => import("./pages/BudgetsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="clubs" replace /> },
  { path: "clubs", element: guarded("gymkhana.club.view", <ClubsPage />) },
  { path: "manage", element: guarded("gymkhana.club.approve", <ManagementPage />) },
  { path: "activities", element: guarded("gymkhana.session.book", <ActivityPage />) },
  { path: "memberships", element: guarded("gymkhana.membership.approve", <MembershipsPage />) },
  { path: "budgets", element: guarded("gymkhana.budget.request", <BudgetsPage />) },
  { path: "reports", element: guarded("gymkhana.report.submit", <ReportsPage />) },
  { path: "polls", element: guarded("gymkhana.poll.vote", <PollsPage />) },
];
