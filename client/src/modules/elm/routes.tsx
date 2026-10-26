import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveBalance = lazy(() => import("./LeaveBalance"));
const LeaveApplication = lazy(() => import("./LeaveApplication"));
const LeaveHistory = lazy(() => import("./LeaveHistory"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="balance" replace /> },
  { path: "balance", element: <LeaveBalance /> },
  { path: "application", element: <LeaveApplication /> },
  { path: "history", element: <LeaveHistory /> },
];
