import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const CourseListPage = lazy(() => import("./pages/CourseListPage"));
const CourseWorkspacePage = lazy(() => import("./pages/CourseWorkspacePage"));
const AssignmentDetailPage = lazy(() => import("./pages/AssignmentDetailPage"));
const GradingPage = lazy(() => import("./pages/GradingPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: <CourseListPage /> },
  { path: "workspace", element: <CourseWorkspacePage /> },
  { path: "assignments", element: <AssignmentDetailPage /> },
  { path: "grading", element: office("lms.grade.view", <GradingPage />) },
];
