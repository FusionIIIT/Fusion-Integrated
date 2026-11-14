import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const RequestsPage = lazy(() => import("./pages/RequestsPage"));

export const routes: RouteObject[] = [
  { path: "balances", element: <BalancesPage /> },
  { path: "requests", element: <RequestsPage /> },
];
