import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeave = lazy(() => import("./pages/ApplyLeave"));
const MyLeaves = lazy(() => import("./pages/MyLeaves"));
const ApproveLeaves = lazy(() => import("./pages/ApproveLeaves"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-leaves" replace /> },
  { path: "apply", element: <ApplyLeave /> },
  { path: "my-leaves", element: <MyLeaves /> },
  { path: "approve-leaves", element: <ApproveLeaves /> },
];