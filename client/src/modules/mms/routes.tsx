import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page. Vite can split these only if import() argument is static literal. */
const SpecialFoodRequestPage = lazy(() => import("./pages/SpecialFoodRequestPage"));
const MyRequestsPage = lazy(() => import("./pages/MyRequestsPage"));
const MyBillsPage = lazy(() => import("./pages/MyBillsPage"));
const WeeklyMenuPage = lazy(() => import("./pages/WeeklyMenuPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const SurveyResponsePage = lazy(() => import("./pages/SurveyResponsePage"));

const RegistrationApprovalsPage = lazy(() => import("./pages/RegistrationApprovalsPage"));
const DeregistrationApprovalsPage = lazy(() => import("./pages/DeregistrationApprovalsPage"));
const RebateApprovalsPage = lazy(() => import("./pages/RebateApprovalsPage"));
const SpecialFoodApprovalsPage = lazy(() => import("./pages/SpecialFoodApprovalsPage"));
const MenuManagementPage = lazy(() => import("./pages/MenuManagementPage"));
const BillingReviewPage = lazy(() => import("./pages/BillingReviewPage"));
const SurveyManagementPage = lazy(() => import("./pages/SurveyManagementPage"));
const SurveySummaryPage = lazy(() => import("./pages/SurveySummaryPage"));

const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const AnnouncementHistoryPage = lazy(() => import("./pages/AnnouncementHistoryPage"));
const FeedbackReviewPage = lazy(() => import("./pages/FeedbackReviewPage"));
const OperationalReportsPage = lazy(() => import("./pages/OperationalReportsPage"));
const SupervisoryReportsPage = lazy(() => import("./pages/SupervisoryReportsPage"));
const RoleAssignmentPage = lazy(() => import("./pages/RoleAssignmentPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  // Student
  { path: "special-food-request", element: guarded("mms.special_food.create", <SpecialFoodRequestPage />) },
  { path: "requests", element: guarded("mms.request.view_self", <MyRequestsPage />) },
  { path: "bills", element: guarded("mms.billing.view_self", <MyBillsPage />) },
  { path: "menu", element: guarded("mms.menu.view", <WeeklyMenuPage />) },
  { path: "feedback", element: guarded("mms.feedback.create", <FeedbackPage />) },
  { path: "survey-response", element: guarded("mms.survey_response.create", <SurveyResponsePage />) },

  // Caretaker
  { path: "registration-approvals", element: guarded("mms.registration.review", <RegistrationApprovalsPage />) },
  { path: "deregistration-approvals", element: guarded("mms.deregistration.review", <DeregistrationApprovalsPage />) },
  { path: "rebate-approvals", element: guarded("mms.rebate.review", <RebateApprovalsPage />) },
  { path: "special-food-approvals", element: guarded("mms.special_food.review", <SpecialFoodApprovalsPage />) },
  { path: "menu-management", element: guarded("mms.menu.manage", <MenuManagementPage />) },
  { path: "billing-review", element: guarded("mms.billing.review", <BillingReviewPage />) },
  { path: "survey-management", element: guarded("mms.survey.create", <SurveyManagementPage />) },
  { path: "survey-summary", element: guarded("mms.survey.view_summary", <SurveySummaryPage />) },
  { path: "announcements", element: guarded("mms.announcement.publish", <AnnouncementsPage />) },
  { path: "operational-reports", element: guarded("mms.report.operational", <OperationalReportsPage />) },

  // Warden & shared
  { path: "announcements/history", element: guarded("mms.announcement.view", <AnnouncementHistoryPage />) },
  { path: "feedback-review", element: guarded("mms.feedback.view", <FeedbackReviewPage />) },
  { path: "supervisory-reports", element: guarded("mms.report.supervisory", <SupervisoryReportsPage />) },

  // Mess Admin
  { path: "role-assignment", element: guarded("mms.role.assign", <RoleAssignmentPage />) },
];
