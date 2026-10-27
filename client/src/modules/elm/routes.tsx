import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ELMPage = lazy(() => import("./pages/ELMPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <ELMPage view="requests" /> },
  { path: "balances", element: <ELMPage view="balances" /> },
  { path: "substitute-queue", element: <ELMPage view="substitute" /> },
  { path: "unit-head-queue", element: <ELMPage view="unit_head" /> },
  { path: "sanction-queue", element: <ELMPage view="sanction" /> },
];
