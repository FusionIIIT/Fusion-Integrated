import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const RequestsPage = lazy(() => import("./pages/RequestsPage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const OfflinePage = lazy(() => import("./pages/OfflinePage"));
const ConfigPage = lazy(() => import("./pages/ConfigPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="balances" replace /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "requests", element: <RequestsPage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "records", element: <RecordsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "offline", element: <OfflinePage /> },
  { path: "config", element: <ConfigPage /> },
];
