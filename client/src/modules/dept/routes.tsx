import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page; Vite splits on static import() literals only. */
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const StockPage = lazy(() => import("./pages/StockPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *  Each has a matching nav item in modules/dept/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "stock", element: <StockPage /> },
  { path: "feedback", element: <FeedbackPage /> },
];
