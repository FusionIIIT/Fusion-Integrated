import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const StockRequestsPage = lazy(() => import("./pages/StockRequestsPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const TimetablePage = lazy(() => import("./pages/TimetablePage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "stock-requests", element: <StockRequestsPage /> },
  { path: "feedback", element: <FeedbackPage /> },
  { path: "timetable", element: <TimetablePage /> },
];
