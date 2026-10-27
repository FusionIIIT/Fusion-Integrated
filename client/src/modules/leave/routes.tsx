import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const SubstitutePage = lazy(() => import("./pages/SubstitutePage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-leaves" replace /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "my-leaves", element: <MyLeavesPage /> },
  { path: "substitute", element: <SubstitutePage /> },
  { path: "reviews", element: <ReviewsPage /> },
];
