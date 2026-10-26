import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only code-split static import() literals. */
const ApplyLeave = lazy(() => import("./ApplyLeave"));
const LeaveList  = lazy(() => import("./LeaveList"));

/** Paths are relative — the shell mounts them under /elm (see registry.ts).
 *
 *  Each path here MUST have a matching nav item in modules/elm/registry.py.
 *  The check in ops/checks/nav_matches_routes.py enforces that invariant.
 *
 *  nav items          →   path here
 *  /elm/apply         →   apply
 *  /elm/leaves        →   leaves
 *  /elm/balances      →   (balances — redirects to leaves for now; no page yet)
 *  /elm/approvals     →   approvals → reuses LeaveList (approver view)
 *  /elm/types         →   (types — not yet implemented; redirect to index)
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply",     element: <ApplyLeave /> },
  { path: "leaves",    element: <LeaveList /> },
  { path: "balances",  element: <Navigate to="../leaves" replace /> },
  { path: "approvals", element: <LeaveList /> },
  { path: "types",     element: <Navigate to="../leaves" replace /> },
];
