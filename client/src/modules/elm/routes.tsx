import { lazy, type RouteObject } from "react";
import { Navigate } from "react-router-dom";

const LeavePage = lazy(() => import("./pages/LeavePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <LeavePage /> },
  { path: "tasks", element: <LeavePage /> },
];
