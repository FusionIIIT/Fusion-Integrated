import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const CoursesListPage = lazy(() => import("./pages/CoursesListPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const GradesPage = lazy(() => import("./pages/GradesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="courses" replace /> },
  { path: "courses", element: <CoursesListPage /> },
  { path: "assignments", element: <AssignmentsPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "grades", element: <GradesPage /> },
];
