import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const CoursesPage = lazy(() => import("./pages/CoursesPage"));
const MaterialsPage = lazy(() => import("./pages/MaterialsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const MyGradesPage = lazy(() => import("./pages/MyGradesPage"));
const GradingPage = lazy(() => import("./pages/GradingPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: guarded("lms.workspace.view", <CoursesPage />) },
  { path: "materials", element: guarded("lms.material.view", <MaterialsPage />) },
  { path: "announcements", element: guarded("lms.announcement.view", <AnnouncementsPage />) },
  { path: "assignments", element: guarded("lms.assignment.view", <AssignmentsPage />) },
  { path: "grades", element: guarded("lms.grade.view", <MyGradesPage />) },
  { path: "grading", element: guarded("lms.submission.review", <GradingPage />) },
];
