import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const QueuePage = lazy(() => import("./pages/QueuePage"));
const ResumptionsPage = lazy(() => import("./pages/ResumptionsPage"));
const PoliciesPage = lazy(() => import("./pages/PoliciesPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const OfflinePage = lazy(() => import("./pages/OfflinePage"));
const AccountsPage = lazy(() => import("./pages/AccountsPage"));

/** Relative paths; each one has a matching nav item in modules/elm/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "queue", element: <QueuePage /> },
  { path: "resumptions", element: <ResumptionsPage /> },
  { path: "policies", element: <PoliciesPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "offline", element: <OfflinePage /> },
  { path: "accounts", element: <AccountsPage /> },
];
