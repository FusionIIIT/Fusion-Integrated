import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const LeaveApplicationsPage = lazy(() => import("./pages/LeaveApplicationsPage"));

export const routes: RouteObject[] = [
  { path: "leave-applications", element: <LeaveApplicationsPage /> },
];
