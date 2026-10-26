import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const ApprovalsInboxPage = lazy(() => import("./pages/ApprovalsInboxPage"));
const LeaveAdminPage = lazy(() => import("./pages/LeaveAdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
  { path: "approvals", element: <ApprovalsInboxPage /> },
  { path: "admin", element: <LeaveAdminPage /> },
];
