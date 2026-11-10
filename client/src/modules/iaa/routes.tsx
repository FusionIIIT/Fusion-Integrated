import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const Workspace = lazy(() => import("./Workspace"));
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="workspace" replace /> },
  { path: "workspace", element: <Workspace /> },
];
