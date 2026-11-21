import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const SubmitApplicationPage = lazy(() => import("./pages/SubmitApplicationPage"));
const ReviewPage = lazy(() => import("./pages/ReviewPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AttorneyPage = lazy(() => import("./pages/AttorneyPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "submit", element: <SubmitApplicationPage /> },
  { path: "review", element: <ReviewPage /> },
  { path: "admin", element: <AdminPage /> },
  { path: "attorney", element: <AttorneyPage /> },
];
