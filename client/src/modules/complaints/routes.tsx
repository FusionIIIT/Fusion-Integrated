import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyComplaintsPage = lazy(() => import("./pages/MyComplaintsPage"));
const ComplaintQueuePage = lazy(() => import("./pages/ComplaintQueuePage"));
const SupervisorPage = lazy(() => import("./pages/SupervisorPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyComplaintsPage /> },
  { path: "queue", element: <ComplaintQueuePage /> },
  { path: "supervisor", element: <SupervisorPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "reports", element: <ReportsPage /> },
  { path: "roles", element: <RolesPage /> },
];
