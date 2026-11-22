import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const MyMessPage = lazy(() => import("./pages/MyMessPage"));
const OperationsPage = lazy(() => import("./pages/OperationsPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <MyMessPage /> },
  { path: "operations", element: <OperationsPage /> },
  { path: "roles", element: <RolesPage /> },
];
