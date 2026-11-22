import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const CoursesPage = lazy(() => import("./pages/CoursesPage"));
const TeachingPage = lazy(() => import("./pages/TeachingPage"));
const GradingPage = lazy(() => import("./pages/GradingPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: <RequirePermission permission="lms.course.view"><CoursesPage /></RequirePermission> },
  { path: "teaching", element: <RequirePermission permission="lms.course.update"><TeachingPage /></RequirePermission> },
  { path: "grading", element: <RequirePermission permission="lms.grade.update"><GradingPage /></RequirePermission> },
];
