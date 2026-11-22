import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const ClubsDashboard = lazy(() => import("./ClubsDashboard"));
const ClubManagement = lazy(() => import("./ClubManagement"));
const VotingPolls = lazy(() => import("./VotingPolls"));

export const routes: RouteObject[] = [
  { index: true, element: <ClubsDashboard /> },
  {
    path: "manage",
    element: (
      <RequirePermission permission="gymkhana.club.manage">
        <ClubManagement />
      </RequirePermission>
    ),
  },
  { path: "polls", element: <VotingPolls /> },
  { path: "*", element: <Navigate to="/gymkhana" replace /> },
];
