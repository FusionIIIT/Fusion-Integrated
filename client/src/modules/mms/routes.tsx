import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const StudentPage = lazy(() => import("./pages/StudentPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="student" replace /> },
  { path: "student", element: <StudentPage /> },
  { path: "operations", element: <OperationsPage /> },
  { path: "roles", element: <RolesPage /> },
];
