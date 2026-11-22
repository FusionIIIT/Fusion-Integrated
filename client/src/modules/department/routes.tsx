import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const AnnouncementsPage = lazy(() => import("./AnnouncementsPage"));
const InventoryPage = lazy(() => import("./StockPages").then((module) => ({ default: module.InventoryPage })));
const StockRequestsPage = lazy(() => import("./StockPages").then((module) => ({ default: module.StockRequestsPage })));
const SubmitFeedbackPage = lazy(() => import("./FeedbackPages").then((module) => ({ default: module.SubmitFeedbackPage })));
const FeedbackInboxPage = lazy(() => import("./FeedbackPages").then((module) => ({ default: module.FeedbackInboxPage })));
const NoticesPage = lazy(() => import("./NoticesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: (
    <RequirePermission permission="department.announcement.view">
      <AnnouncementsPage />
    </RequirePermission>
  ) },
  { path: "inventory", element: (
    <RequirePermission permission="department.stock.view"><InventoryPage /></RequirePermission>
  ) },
  { path: "stock-requests", element: (
    <RequirePermission permission="department.stock_request.view"><StockRequestsPage /></RequirePermission>
  ) },
  { path: "feedback", element: (
    <RequirePermission permission="department.feedback.create"><SubmitFeedbackPage /></RequirePermission>
  ) },
  { path: "feedback-inbox", element: (
    <RequirePermission permission="department.feedback.view"><FeedbackInboxPage /></RequirePermission>
  ) },
  { path: "notices", element: (
    <RequirePermission permission="department.notice.view"><NoticesPage /></RequirePermission>
  ) },
];
