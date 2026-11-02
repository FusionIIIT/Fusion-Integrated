import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ClubsDashboard = lazy(() => import("./ClubsDashboard"));
const ClubManagement = lazy(() => import("./ClubManagement"));
const VotingPolls = lazy(() => import("./VotingPolls"));

export const routes: RouteObject[] = [
  { index: true, element: <ClubsDashboard /> },
  { path: "manage", element: <ClubManagement /> },
  { path: "polls", element: <VotingPolls /> },
  { path: "*", element: <Navigate to="/gymkhana" replace /> },
];
