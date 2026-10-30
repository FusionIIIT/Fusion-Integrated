import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const CalendarsPage = lazy(() => import("./pages/CalendarsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-leaves" replace /> },
  { path: "my-leaves", element: <MyLeavesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "admin", element: <AdminPage /> },
  { path: "calendars", element: <CalendarsPage /> },
];
