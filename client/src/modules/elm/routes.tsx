import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const Requests = lazy(() => import("./pages").then((m) => ({default: m.Requests})));
const Balances = lazy(() => import("./pages").then((m) => ({default: m.Balances})));
const Tasks = lazy(() => import("./pages").then((m) => ({default: m.Tasks})));
const Notifications = lazy(() => import("./pages").then((m) => ({default: m.LeaveNotifications})));
const Configuration = lazy(() => import("./pages").then((m) => ({default: m.LeaveConfiguration})));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <Requests /> },
  { path: "balances", element: <Balances /> },
  { path: "tasks", element: <Tasks /> },
  { path: "notifications", element: <Notifications /> },
  { path: "configuration", element: <Configuration /> },
];
