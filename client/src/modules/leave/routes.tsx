import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "applications", element: <MyApplicationsPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
