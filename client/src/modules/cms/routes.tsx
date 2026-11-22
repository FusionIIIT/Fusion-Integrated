import { lazy, type ReactNode } from "react";
import type { RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const CmsHome = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.CmsHomePage })));
const MyComplaints = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.MyComplaintsPage })));
const SubmitComplaint = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.SubmitComplaintPage })));
const Worklist = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.WorklistPage })));
const Escalations = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.EscalationsPage })));
const Reopening = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.ReopeningReviewPage })));
const Feedback = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.FeedbackPage })));
const Announcements = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.AnnouncementsPage })));
const Reports = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.ReportsPage })));
const Roles = lazy(() => import("./pages/CmsPages").then((m) => ({ default: m.CmsRolesPage })));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <CmsHome /> },
  { path: "mine", element: guarded("cms.complaint.track", <MyComplaints />) },
  { path: "submit", element: guarded("cms.complaint.submit", <SubmitComplaint />) },
  { path: "worklist", element: guarded("cms.complaint.view", <Worklist />) },
  { path: "escalations", element: guarded("cms.escalation.monitor", <Escalations />) },
  { path: "reopening", element: guarded("cms.reopening.review", <Reopening />) },
  { path: "feedback", element: guarded("cms.feedback.review", <Feedback />) },
  { path: "announcements", element: guarded("cms.announcement.view", <Announcements />) },
  { path: "reports", element: guarded("cms.report.view", <Reports />) },
  { path: "roles", element: guarded("cms.role.manage", <Roles />) },
];
