import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const AnnouncementsPage = lazy(() => import("./AnnouncementsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: (
    <RequirePermission permission="department.announcement.view">
      <AnnouncementsPage />
    </RequirePermission>
  ) },
];
