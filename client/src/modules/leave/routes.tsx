import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <LeaveRequestsPage /> },
];
