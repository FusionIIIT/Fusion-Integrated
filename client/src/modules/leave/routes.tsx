import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const TasksPage = lazy(() => import("./pages/TasksPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));

export const routes: RouteObject[] = [
  { index: true, element: <MyLeavePage /> },
  { path: "tasks", element: <TasksPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "balances", element: <MyLeavePage /> },
  { path: "calendar", element: <CalendarPage /> },
];
