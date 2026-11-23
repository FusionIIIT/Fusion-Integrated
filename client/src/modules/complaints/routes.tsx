import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyComplaintsPage = lazy(() => import("./pages/MyComplaintsPage"));
const ComplaintQueuePage = lazy(() => import("./pages/ComplaintQueuePage"));
const SupervisorPage = lazy(() => import("./pages/SupervisorPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyComplaintsPage /> },
  { path: "queue", element: office("complaints.complaint.assign", <ComplaintQueuePage />) },
  { path: "supervisor", element: office("complaints.complaint.supervise", <SupervisorPage />) },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "reports", element: office("complaints.complaint.report", <ReportsPage />) },
  { path: "roles", element: office("complaints.role.manage", <RolesPage />) },
];
