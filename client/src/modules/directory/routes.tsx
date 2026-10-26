import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const DirectoryPage = lazy(() => import("./pages/DirectoryPage"));

export const routes: RouteObject[] = [
  { index: true, element: <DirectoryPage /> },
];
