import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const HolidaysPage = lazy(() => import("./pages/HolidaysPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "holidays", element: <HolidaysPage /> },
];
