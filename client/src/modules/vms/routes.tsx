import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyVisitsPage = lazy(() => import("./pages/MyVisitsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const GatePage = lazy(() => import("./pages/GatePage"));
const RosterPage = lazy(() => import("./pages/RosterPage"));
const MusterPage = lazy(() => import("./pages/MusterPage"));
const EventsPage = lazy(() => import("./pages/EventsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

/** Paths are RELATIVE — the shell mounts them under /vms. Each has a matching
 *  nav item in the server's modules/vms/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="visits" replace /> },
  { path: "visits", element: <MyVisitsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "gate", element: <GatePage /> },
  { path: "roster", element: <RosterPage /> },
  { path: "muster", element: <MusterPage /> },
  { path: "events", element: <EventsPage /> },
  { path: "reports", element: <ReportsPage /> },
  { path: "admin", element: <AdminPage /> },
];
