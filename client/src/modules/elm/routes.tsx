import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <LeaveRequestsPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
