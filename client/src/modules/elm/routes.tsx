import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));
const LeaveRequestForm = lazy(() => import("./components/LeaveRequestForm"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <LeaveRequestsPage /> },
  { path: "request/new", element: <LeaveRequestForm /> },
];
