import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ClubDirectoryPage = lazy(() => import("./pages/ClubDirectoryPage"));
const ClubDetailsPage = lazy(() => import("./pages/ClubDetailsPage"));

export const routes: RouteObject[] = [
  {
    index: true,
    element: <Navigate to="dashboard" replace />,
  },
  {
    path: "dashboard",
    element: <DashboardPage />,
  },
  {
    path: "clubs",
    element: <ClubDirectoryPage />,
  },
  {
    path: "clubs/:clubId",
    element: <ClubDetailsPage />,
  },
];
