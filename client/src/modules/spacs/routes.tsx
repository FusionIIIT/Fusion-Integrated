import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const CataloguePage = lazy(() => import("./pages/CataloguePage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="catalogue" replace /> },
  { path: "catalogue", element: <CataloguePage /> },
  { path: "applications", element: <ApplicationsPage /> },
];
