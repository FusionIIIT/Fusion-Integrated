import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const CoursePage = lazy(() => import("./pages/CoursePage"));
const MaterialsPage = lazy(() => import("./pages/MaterialsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const GradebookPage = lazy(() => import("./pages/GradebookPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses/:id", element: <CoursePage /> },
  { path: "courses/:id/materials", element: <MaterialsPage /> },
  { path: "courses/:id/announcements", element: <AnnouncementsPage /> },
  { path: "courses/:id/assignments", element: <AssignmentsPage /> },
  { path: "courses/:id/gradebook", element: office("lms.grade.view", <GradebookPage />) },
];