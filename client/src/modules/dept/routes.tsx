import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const StockRequestsPage = lazy(() => import("./pages/StockRequestsPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const TimetablePage = lazy(() => import("./pages/TimetablePage"));
const LabResourcesPage = lazy(() => import("./pages/LabResourcesPage"));
const ProfilesPage = lazy(() => import("./pages/ProfilesPage"));
const DepartmentDetailsPage = lazy(() => import("./pages/DepartmentDetailsPage"));
const RoleGovernancePage = lazy(() => import("./pages/RoleGovernancePage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "inventory", element: guarded("dept.inventory.view", <InventoryPage />) },
  { path: "stock-requests", element: guarded("dept.stock_request.view", <StockRequestsPage />) },
  { path: "feedback", element: <FeedbackPage /> },
  { path: "timetables", element: <TimetablePage /> },
  { path: "labs", element: <LabResourcesPage /> },
  { path: "profiles", element: <ProfilesPage /> },
  { path: "details", element: <DepartmentDetailsPage /> },
  { path: "roles", element: guarded("dept.role_assignment.view", <RoleGovernancePage />) },
];
