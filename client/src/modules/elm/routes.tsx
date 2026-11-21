import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";


const LeavePage = lazy(() => import("./pages/LeavePage"));
const LeaveTasksPage = lazy(() => import("./pages/LeaveTasksPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <LeavePage /> },
  { path: "tasks", element: <LeaveTasksPage /> },
];
