import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page; the import() argument must stay a static literal
 *  or Vite cannot split it. */
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const SubstituteRequestsPage = lazy(
  () => import("./pages/SubstituteRequestsPage"));
const ApprovalQueuePage = lazy(() => import("./pages/ApprovalQueuePage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *  Every entry has a matching nav item in modules/leave/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "substitutions", element: <SubstituteRequestsPage /> },
  { path: "requests", element: <ApprovalQueuePage kind="requests" /> },
  { path: "sanctions", element: <ApprovalQueuePage kind="sanctions" /> },
  { path: "holidays", element: <HolidayCalendarPage /> },
];
