import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const ResumptionsPage = lazy(() => import("./pages/ResumptionsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "calendar", element: <AdminPage /> },
  { path: "resumptions", element: <ResumptionsPage /> },
  { path: "admin", element: <AdminPage /> },
];
