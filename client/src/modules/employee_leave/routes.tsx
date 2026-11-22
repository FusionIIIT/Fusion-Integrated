import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const BalancePage = lazy(() => import("./pages/BalancePage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "balances", element: <BalancePage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "admin", element: <AdminPage /> },
];