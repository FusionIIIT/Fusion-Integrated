import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const DepartmentPage = lazy(() => import("./DepartmentPage"));

export const routes: RouteObject[] = [
  { index: true, element: <DepartmentPage /> },
];

