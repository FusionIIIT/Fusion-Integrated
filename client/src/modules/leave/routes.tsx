import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeavePage = lazy(() => import("./LeavePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <LeavePage view="apply" /> },
  { path: "mine", element: <LeavePage view="mine" /> },
  { path: "balances", element: <LeavePage view="balances" /> },
  { path: "substitute", element: <LeavePage view="substitute" /> },
  { path: "approvals", element: <LeavePage view="approvals" /> },
  { path: "calendar", element: <LeavePage view="calendar" /> },
  { path: "admin", element: <LeavePage view="admin" /> },
];
