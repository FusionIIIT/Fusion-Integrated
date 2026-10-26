import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const LeaveApplicationsPage = lazy(
  () => import("./pages/LeaveApplicationsPage")
);
const ApplyLeavePage = lazy(() => import("./pages/ApplyLeavePage"));
const LeaveBalancesPage = lazy(() => import("./pages/LeaveBalancesPage"));
const SubstituteApprovalsPage = lazy(
  () => import("./pages/SubstituteApprovalsPage")
);
const UnitHeadReviewsPage = lazy(
  () => import("./pages/UnitHeadReviewsPage")
);
const LeaveSanctionsPage = lazy(() => import("./pages/LeaveSanctionsPage"));

export const routes: RouteObject[] = [
  {
    index: true,
    element: <Navigate to="applications" replace />,
  },
  {
    path: "applications",
    element: <LeaveApplicationsPage />,
  },
  {
    path: "apply",
    element: <ApplyLeavePage />,
  },
  {
    path: "balances",
    element: <LeaveBalancesPage />,
  },
  {
    path: "substitute",
    element: <SubstituteApprovalsPage />,
  },
  {
    path: "unit-head-reviews",
    element: <UnitHeadReviewsPage />,
  },
  {
    path: "sanctions",
    element: <LeaveSanctionsPage />,
  },
];
