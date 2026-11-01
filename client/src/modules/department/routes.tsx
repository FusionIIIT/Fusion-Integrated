import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const RequestSeminarPage = lazy(() => import("./pages/RequestSeminarPage"));
const MySeminarRequestsPage = lazy(() => import("./pages/MySeminarRequestsPage"));
const PendingSchedulingPage = lazy(() => import("./pages/PendingSchedulingPage"));
const SeminarCalendarPage = lazy(() => import("./pages/SeminarCalendarPage"));
const AllocationsPage = lazy(() => import("./pages/AllocationsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py:
 *  - /department/seminar-request -> RequestSeminarPage
 *  - /department/my-seminars     -> MySeminarRequestsPage
 *  - /department/pending-seminars -> PendingSchedulingPage
 *  - /department/calendar        -> SeminarCalendarPage
 *  - /department/allocations     -> AllocationsPage
 *  - /department/announcements   -> AnnouncementsPage
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="calendar" replace /> },
  { path: "seminar-request", element: <RequestSeminarPage /> },
  { path: "my-seminars", element: <MySeminarRequestsPage /> },
  { path: "pending-seminars", element: <PendingSchedulingPage /> },
  { path: "calendar", element: <SeminarCalendarPage /> },
  { path: "allocations", element: <AllocationsPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
];
