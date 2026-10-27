import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ELMPage = lazy(() => import("./pages/ELMPage"));
const ELMAdminPage = lazy(() => import("./pages/ELMAdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <ELMPage /> },
  { path: "apply", element: <ELMPage /> },
  { path: "substitute", element: <ELMAdminPage /> },
  { path: "approvals", element: <ELMAdminPage /> },
  { path: "admin", element: <ELMAdminPage /> },
];
