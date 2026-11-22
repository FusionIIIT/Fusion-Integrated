import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const CourseWorkspacePage = lazy(() => import("./pages/CourseWorkspacePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: <CourseWorkspacePage /> },
];
