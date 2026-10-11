import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
];
