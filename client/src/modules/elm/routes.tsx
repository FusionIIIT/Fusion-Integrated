import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const SanctionsPage = lazy(() => import("./pages/SanctionsPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const SlaPage = lazy(() => import("./pages/SlaPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my" replace /> },
  { path: "my", element: <MyLeavePage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "sanctions", element: <SanctionsPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "records", element: <RecordsPage /> },
  { path: "policy", element: <PolicyPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "sla", element: <SlaPage /> },
];
