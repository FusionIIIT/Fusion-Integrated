import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const LeaveBalancePage = lazy(() => import("./pages/LeaveBalancePage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const PendingApprovalsPage = lazy(() => import("./pages/PendingApprovalsPage"));
const AllLeavesPage = lazy(() => import("./pages/AllLeavesPage"));
const HolidayCalendarPage = lazy(() => import("./pages/HolidayCalendarPage"));
const RecordOfflinePage = lazy(() => import("./pages/RecordOfflinePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-leaves" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "my-leaves", element: <MyLeavesPage /> },
  { path: "balance", element: <LeaveBalancePage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
  { path: "pending", element: <PendingApprovalsPage /> },
  { path: "all-leaves", element: <AllLeavesPage /> },
  { path: "calendar", element: <HolidayCalendarPage /> },
  { path: "offline", element: <RecordOfflinePage /> },
];
