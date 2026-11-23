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

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="clubs" replace /> },
  { path: "clubs", element: <ClubsPage /> },
  { path: "memberships", element: <MembershipsPage /> },
  { path: "polls", element: <PollsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "manage", element: office("gymkhana.club.manage", <ClubManagementPage />) },
  { path: "admin", element: office("gymkhana.club.approve", <ClubAdminPage />) },
  { path: "reports", element: office("gymkhana.report.view", <FacultyReportsPage />) },
];
