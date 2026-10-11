import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ELMPage = lazy(() => import("./pages/ELMPage"));

/** Paths are relative to the /elm basePath in the server module registry. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-requests" replace /> },
  { path: "my-requests", element: <ELMPage /> },
  { path: "apply", element: <ELMPage /> },
  { path: "review", element: <ELMPage /> },
  { path: "admin", element: <ELMPage /> },
];
