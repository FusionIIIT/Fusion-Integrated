import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));

export const routes: RouteObject[] = [
  { path: "leave-requests", element: <LeaveRequestsPage /> },
];
