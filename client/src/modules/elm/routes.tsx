import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const SubstitutePage = lazy(() => import("./pages/SubstitutePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "substitute-requests", element: <SubstitutePage /> },
  { path: "unit-head-reviews", element: <ApprovalsPage role="unit_head" /> },
  { path: "establishment-routing", element: <ApprovalsPage role="establishment" /> },
  { path: "sanction-decisions", element: <ApprovalsPage role="sanction" /> },
  { path: "admin", element: <AdminPage /> },
];
