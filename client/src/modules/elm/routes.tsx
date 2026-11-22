import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const ApplyLeave = lazy(() => import("./pages/ApplyLeave"));

export const routes: RouteObject[] = [
  {
    index: true,
    element: <Dashboard />,
  },
  {
    path: "apply",
    element: <ApplyLeave />,
  },
  {
    path: "requests",
    element: <Dashboard />,
  },
  {
    path: "substitute",
    element: <Dashboard />,
  },
  {
    path: "approvals",
    element: <Dashboard />,
  },
];
