import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const MyLeavesPage = lazy(() => import("./pages/MyLeavesPage"));
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
const UnitHeadReviewPage = lazy(() => import("./pages/UnitHeadReviewPage"));
const SanctionPage = lazy(() => import("./pages/SanctionPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "my-leaves", element: <MyLeavesPage /> },
  { path: "substitute-requests", element: <SubstituteRequestsPage /> },
  { path: "unit-head-review", element: <UnitHeadReviewPage /> },
  { path: "sanction", element: <SanctionPage /> },
  { path: "approvals", element: <Navigate to="../unit-head-review" replace /> },
];
