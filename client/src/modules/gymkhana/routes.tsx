import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const ClubsPage = lazy(() => import("./pages/ClubsPage"));
const MembershipsPage = lazy(() => import("./pages/MembershipsPage"));
const PollsPage = lazy(() => import("./pages/PollsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const ClubManagementPage = lazy(() => import("./pages/ClubManagementPage"));
const ClubAdminPage = lazy(() => import("./pages/ClubAdminPage"));
const FacultyReportsPage = lazy(() => import("./pages/FacultyReportsPage"));

// Every page is for the roles its nav item's required_permission names (registry.py).
function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="clubs" replace /> },
  { path: "clubs", element: office("gymkhana.club.view", <ClubsPage />) },
  { path: "memberships", element: office("gymkhana.membership.view", <MembershipsPage />) },
  { path: "polls", element: office("gymkhana.poll.view", <PollsPage />) },
  { path: "calendar", element: office("gymkhana.booking.view", <CalendarPage />) },
  { path: "manage", element: office("gymkhana.club.manage", <ClubManagementPage />) },
  { path: "admin", element: office("gymkhana.club.approve", <ClubAdminPage />) },
  { path: "reports", element: office("gymkhana.report.view", <FacultyReportsPage />) },
];
