import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const BalancePage = lazy(() => import("./pages/BalancePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence is checked by ops/checks/nav_matches_routes.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balance", element: <BalancePage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
