import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveRequestsPage = lazy(() => import("./pages/LeaveRequestsPage"));
const LeaveHistoryPage = lazy(() => import("./pages/LeaveHistoryPage"));
const LeaveInboxPage = lazy(() => import("./pages/LeaveInboxPage"));
const LeaveAccountsPage = lazy(() => import("./pages/LeaveAccountsPage"));
const LeaveConfigurationPage = lazy(() => import("./pages/LeaveConfigurationPage"));

export const routes: RouteObject[] = [
  { index: true, element: <LeaveRequestsPage /> },
  { path: "history", element: <LeaveHistoryPage /> },
  { path: "inbox", element: <LeaveInboxPage /> },
  { path: "accounts", element: <LeaveAccountsPage /> },
  { path: "configuration", element: <LeaveConfigurationPage /> },
  { path: "*", element: <Navigate to="/elm" replace /> },
];
