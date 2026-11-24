import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ElmPage = lazy(() => import("./ElmPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ElmPage view="apply" /> },
  { path: "mine", element: <ElmPage view="mine" /> },
  { path: "balance", element: <ElmPage view="balance" /> },
  { path: "approvals", element: <ElmPage view="approvals" /> },
  { path: "admin", element: <ElmPage view="admin" /> },
];
