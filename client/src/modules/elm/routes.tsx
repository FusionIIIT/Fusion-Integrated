import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveApplicationPage = lazy(() => import("./leave-application"));
const MyLeaveApplicationsPage = lazy(() => import("./my-leave-applications"));
const ApproveLeavePage = lazy(() => import("./approve-leave"));
const AppliesPage = lazy(() => import("./applies"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="leave-application" replace /> },
  { path: "leave-application", element: <LeaveApplicationPage /> },
  { path: "apply", element: <LeaveApplicationPage /> },
  { path: "applications", element: <AppliesPage /> },
  { path: "my-leave-applications", element: <MyLeaveApplicationsPage /> },
  { path: "my-applications", element: <MyLeaveApplicationsPage /> },
  { path: "approve-leave", element: <ApproveLeavePage /> },
  { path: "approve", element: <ApproveLeavePage /> },
  { path: "applies", element: <AppliesPage /> },
];
