import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const AccommodationsPage = lazy(() => import("./pages/AccommodationsPage"));
const LeavesPage = lazy(() => import("./pages/LeavesPage"));
const ComplaintsPage = lazy(() => import("./pages/ComplaintsPage"));
const FinesPage = lazy(() => import("./pages/FinesPage"));
const NoticesPage = lazy(() => import("./pages/NoticesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="accommodations" replace /> },
  { path: "accommodations", element: <AccommodationsPage /> },
  { path: "leaves", element: <LeavesPage /> },
  { path: "complaints", element: <ComplaintsPage /> },
  { path: "fines", element: <FinesPage /> },
  { path: "notices", element: <NoticesPage /> },
];
