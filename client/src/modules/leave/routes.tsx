import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const SubstitutePage = lazy(() => import("./pages/SubstitutePage"));
const QueuePage = lazy(() => import("./pages/QueuePage"));
const SanctionPage = lazy(() => import("./pages/SanctionPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const OfflinePage = lazy(() => import("./pages/OfflinePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "substitute", element: <SubstitutePage /> },
  { path: "queue", element: <QueuePage /> },
  { path: "sanction", element: <SanctionPage /> },
  { path: "policy", element: <PolicyPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "offline", element: <OfflinePage /> },
];
