import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));

/** Relative to the manifest's basePath. Each entry matches a nav item in
 *  modules/elm/registry.py; ops/checks/nav_matches_routes.py enforces it. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "approvals", element: <ApprovalsPage /> },
];
