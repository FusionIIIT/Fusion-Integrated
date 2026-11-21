import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));

/** Each path has a matching nav item in modules/leave/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "settings", element: <SettingsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "records", element: <RecordsPage /> },
];
