import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyComplaintsPage = lazy(() => import("./pages/MyComplaintsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const FeedbackReviewPage = lazy(() => import("./pages/FeedbackReviewPage"));
const HandlerWorkQueuePage = lazy(() => import("./pages/HandlerWorkQueuePage"));
const AssignmentQueuePage = lazy(() => import("./pages/AssignmentQueuePage"));
const SupervisionPage = lazy(() => import("./pages/SupervisionPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function protectedPage(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: protectedPage("complaints.complaint.view", <MyComplaintsPage />) },
  { path: "announcements", element: protectedPage("complaints.announcement.view", <AnnouncementsPage />) },
  { path: "feedback", element: protectedPage("complaints.feedback.review", <FeedbackReviewPage />) },
  { path: "work-queue", element: protectedPage("complaints.complaint.update", <HandlerWorkQueuePage />) },
  { path: "assignment-queue", element: protectedPage("complaints.complaint.assign", <AssignmentQueuePage />) },
  { path: "supervision", element: protectedPage("complaints.complaint.approve", <SupervisionPage />) },
  { path: "reports", element: protectedPage("complaints.report.view", <ReportsPage />) },
];
