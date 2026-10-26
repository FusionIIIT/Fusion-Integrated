import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveApplicationsPage = lazy(() => import("./pages/LeaveApplicationsPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "applications", element: <LeaveApplicationsPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
