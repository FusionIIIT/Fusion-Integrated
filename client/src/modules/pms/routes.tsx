import { lazy } from "react";
import type { RouteObject } from "react-router-dom";
import { Navigate } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const SubmitApplicationPage = lazy(() => import("./pages/SubmitApplicationPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <RequirePermission permission="pms.application.view_self"><MyApplicationsPage /></RequirePermission> },
  { path: "submit", element: <RequirePermission permission="pms.application.create"><SubmitApplicationPage /></RequirePermission> },
];
