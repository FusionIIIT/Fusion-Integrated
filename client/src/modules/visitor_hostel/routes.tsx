import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
const BookingsPage = lazy(() => import("./BookingsPage"));
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="bookings" replace /> },
  { path: "bookings", element: <BookingsPage /> },
];
