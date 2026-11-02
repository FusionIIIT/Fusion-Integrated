import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const CourseListPage = lazy(() => import("./pages/CourseListPage"));
const CourseWorkspacePage = lazy(() => import("./pages/CourseWorkspacePage"));
const AssignmentDetailPage = lazy(() => import("./pages/AssignmentDetailPage"));
const GradingPage = lazy(() => import("./pages/GradingPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: <CourseListPage /> },
  { path: "course/:courseId", element: <CourseWorkspacePage /> },
  { path: "assignment/:assignmentId", element: <AssignmentDetailPage /> },
  { path: "grading/:assignmentId", element: <GradingPage /> },
];
