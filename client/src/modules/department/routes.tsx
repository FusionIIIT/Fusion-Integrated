import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const OverviewPage = lazy(() => import("./pages/OverviewPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const TimetablePage = lazy(() => import("./pages/TimetablePage"));
const FacultyStaffPage = lazy(() => import("./pages/FacultyStaffPage"));
const LabResourcesPage = lazy(() => import("./pages/LabResourcesPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath (/department).
 *
 *  Every entry here has a matching nav item in the server's registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="overview" replace /> },
  { path: "overview", element: <OverviewPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "inventory", element: <InventoryPage /> },
  { path: "feedback", element: <FeedbackPage /> },
  { path: "timetable", element: <TimetablePage /> },
  { path: "faculty-staff", element: <FacultyStaffPage /> },
  { path: "resources", element: <LabResourcesPage /> },
];
