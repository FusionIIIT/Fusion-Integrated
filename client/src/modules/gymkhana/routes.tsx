import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ClubsPage = lazy(() => import("./pages/ClubsPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="clubs" replace /> },
  { path: "clubs", element: <ClubsPage /> },
  { path: "my-applications", element: <MyApplicationsPage /> },
  { path: "reviews", element: <ReviewsPage /> },
];
