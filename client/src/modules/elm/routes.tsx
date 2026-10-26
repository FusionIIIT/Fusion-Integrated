import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const LeaveApprovalsPage = lazy(() => import("./pages/LeaveApprovalsPage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balances", element: <LeaveBalancesPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
  { path: "holidays", element: <HolidayCalendarPage /> },
];

