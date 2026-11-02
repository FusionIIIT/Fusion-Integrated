import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "apply", element: <MyLeavePage showApplicationForm /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
