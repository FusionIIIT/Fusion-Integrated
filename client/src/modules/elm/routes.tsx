import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import ElmPlaceholderPage from "./ElmPlaceholderPage";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyRequestsPage = lazy(() => import("./pages/MyRequestsPage"));
const LeaveBalancePage = lazy(() => import("./pages/LeaveBalancePage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const UnitHeadReviewPage = lazy(() => import("./pages/UnitHeadReviewPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyRequestsPage /> },
  { path: "balance", element: <LeaveBalancePage /> },
  { path: "substitute-requests", element: <SubstituteRequestsPage /> },
  { path: "unit-head-review", element: <UnitHeadReviewPage /> },
  { path: "establishment-routing", element: <ElmPlaceholderPage title="Establishment Routing" /> },
  { path: "sanction-decisions", element: <ElmPlaceholderPage title="Final Sanction Decisions" /> },
  { path: "admin/policy", element: <ElmPlaceholderPage title="Leave Policy Administration" /> },
  { path: "admin/holidays", element: <ElmPlaceholderPage title="Holiday & RH Calendar Administration" /> },
  { path: "offline-records", element: <ElmPlaceholderPage title="Offline Leave Recording" /> },
];
