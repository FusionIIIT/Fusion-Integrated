import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveRequestPage = lazy(() => import("./pages/LeaveRequestPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <LeaveRequestPage /> },
];
