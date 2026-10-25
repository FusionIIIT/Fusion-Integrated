import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));

export const routes: RouteObject[] = [
  { path: "", element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
];

export default routes;
