import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page; every path has a nav item in modules/leave/registry.py. */
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));
const HierarchyPage = lazy(() => import("./pages/HierarchyPage"));
const SlaPage = lazy(() => import("./pages/SlaPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "records", element: <RecordsPage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "policy", element: <PolicyPage /> },
  { path: "hierarchy", element: <HierarchyPage /> },
  { path: "sla", element: <SlaPage /> },
];
