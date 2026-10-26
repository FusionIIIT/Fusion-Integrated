import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveRequestList = lazy(() => import("./pages/LeaveRequestList"));
const LeaveRequestForm = lazy(() => import("./pages/LeaveRequestForm"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="leave-requests" replace /> },
  { path: "leave-requests", element: <LeaveRequestList /> },
  { path: "leave-requests/create", element: <LeaveRequestForm /> },
  { path: "leave-requests/:id", element: <LeaveRequestForm /> },
];
