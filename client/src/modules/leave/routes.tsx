import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const SubstitutesPage = lazy(() => import("./pages/SubstitutesPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "substitutes", element: <SubstitutesPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "admin", element: <AdminPage /> },
];
