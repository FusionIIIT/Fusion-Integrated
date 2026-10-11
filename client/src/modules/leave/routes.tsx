import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const ActionInboxPage = lazy(() => import("./pages/ActionInboxPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const ResumptionsPage = lazy(() => import("./pages/ResumptionsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const OfflineRecordsPage = lazy(() => import("./pages/OfflineRecordsPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "inbox", element: <ActionInboxPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "resumptions", element: <ResumptionsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "offline-records", element: <OfflineRecordsPage /> },
  { path: "policy", element: <PolicyPage /> },
];
