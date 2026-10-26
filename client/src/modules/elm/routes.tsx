import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "my-leaves", element: <MyLeavesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
];
