import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page; the import() arguments stay static literals. */
const LeavePage = lazy(() => import("./pages/LeavePage"));
const LeaveDecisionsPage = lazy(() => import("./pages/LeaveDecisionsPage"));
const BonafidePage = lazy(() => import("./pages/BonafidePage"));
const BonafideQueuePage = lazy(() => import("./pages/BonafideQueuePage"));
const NoDuesPage = lazy(() => import("./pages/NoDuesPage"));
const NoDuesQueuePage = lazy(() => import("./pages/NoDuesQueuePage"));
const ClaimsPage = lazy(() => import("./pages/ClaimsPage"));
const ClaimQueuePage = lazy(() => import("./pages/ClaimQueuePage"));
const VerificationsPage = lazy(() => import("./pages/VerificationsPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const SeminarsPage = lazy(() => import("./pages/SeminarsPage"));
const SeminarQueuePage = lazy(() => import("./pages/SeminarQueuePage"));
const SeminarSchedulesPage = lazy(() => import("./pages/SeminarSchedulesPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));

/** Relative paths; each has a nav item in the server's registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="leave" replace /> },
  { path: "leave", element: <LeavePage /> },
  { path: "leave-decisions", element: <LeaveDecisionsPage /> },
  { path: "bonafide", element: <BonafidePage /> },
  { path: "bonafide-queue", element: <BonafideQueuePage /> },
  { path: "no-dues", element: <NoDuesPage /> },
  { path: "no-dues-queue", element: <NoDuesQueuePage /> },
  { path: "claims", element: <ClaimsPage /> },
  { path: "claim-queue", element: <ClaimQueuePage /> },
  { path: "verifications", element: <VerificationsPage /> },
  { path: "assignments", element: <AssignmentsPage /> },
  { path: "seminars", element: <SeminarsPage /> },
  { path: "seminar-queue", element: <SeminarQueuePage /> },
  { path: "seminar-schedules", element: <SeminarSchedulesPage /> },
  { path: "notifications", element: <NotificationsPage /> },
];
