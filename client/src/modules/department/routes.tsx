import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const TimetablePage = lazy(() => import("./pages/TimetablePage"));
const LabsPage = lazy(() => import("./pages/LabsPage"));
const ProfilesPage = lazy(() => import("./pages/ProfilesPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

// Each page is closed at its route with exactly its nav item's required_permission (registry.py).
function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="overview" replace /> },
  { path: "overview", element: guarded("department.department.view", <OverviewPage />) },
  { path: "announcements", element: guarded("department.announcement.view", <AnnouncementsPage />) },
  { path: "inventory", element: guarded("department.inventory_item.view", <InventoryPage />) },
  { path: "feedback", element: guarded("department.feedback.view", <FeedbackPage />) },
  { path: "timetable", element: guarded("department.timetable.view", <TimetablePage />) },
  { path: "labs", element: guarded("department.lab_resource.view", <LabsPage />) },
  { path: "profiles", element: guarded("department.profile.view", <ProfilesPage />) },
  { path: "roles", element: guarded("department.role_assignment.view", <RolesPage />) },
];
