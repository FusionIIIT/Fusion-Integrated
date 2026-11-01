import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="users" replace /> },
  { path: "users", element: <UsersPage /> },
  { path: "roles", element: <RolesPage /> },
];
