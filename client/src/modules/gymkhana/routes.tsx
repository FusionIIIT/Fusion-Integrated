import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { RequirePermission } from "../../auth/RequirePermission";

const ClubsPage = lazy(() => import("./pages/ClubsPage"));
const PollsPage = lazy(() => import("./pages/PollsPage"));
const SchedulePage = lazy(() => import("./pages/SchedulePage"));
const MyClubsPage = lazy(() => import("./pages/MyClubsPage"));
const AdministrationPage = lazy(() => import("./pages/AdministrationPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

const LANDINGS: [string, string][] = [
  ["gymkhana.membership.create", "clubs"],
  ["gymkhana.club.approve", "administration"],
  ["gymkhana.event_report.review", "reports"],
];

// Each role lands on the first page it may open, so no role starts on NotPermitted.
function Landing() {
  const { can } = useAuth();
  const target = LANDINGS.find(([perm]) => can(perm))?.[1] ?? "clubs";
  return <Navigate to={target} replace />;
}

// Every page belongs to one role, so each is closed with its nav item's permission (registry.py).
function only(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Landing /> },
  { path: "clubs", element: only("gymkhana.membership.create", <ClubsPage />) },
  { path: "polls", element: only("gymkhana.vote.create", <PollsPage />) },
  { path: "schedule", element: only("gymkhana.booking.view", <SchedulePage />) },
  { path: "my-clubs", element: only("gymkhana.leadership.assign", <MyClubsPage />) },
  { path: "administration", element: only("gymkhana.club.approve", <AdministrationPage />) },
  { path: "reports", element: only("gymkhana.event_report.review", <ReportsPage />) },
];
