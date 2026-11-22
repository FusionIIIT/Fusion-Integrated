import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const DeptResourcePage = lazy(() => import("./DeptResourcePage"));
function guarded(permission: string, resource: string): ReactNode {
  return <RequirePermission permission={permission}><DeptResourcePage resource={resource} /></RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: guarded("dept.announcement.view", "announcements") },
  { path: "stock", element: guarded("dept.stock_request.view", "stock") },
  { path: "feedback", element: guarded("dept.feedback.view", "feedback") },
  { path: "timetable", element: guarded("dept.timetable.view", "timetable") },
  { path: "resources", element: guarded("dept.resource.view", "resources") },
  { path: "profiles", element: guarded("dept.profile.view", "profiles") },
  { path: "details", element: guarded("dept.department.view", "details") },
];
