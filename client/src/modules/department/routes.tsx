import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { DepartmentLayout, RequireDepartmentPermission } from "./DepartmentLayout";

const AnnouncementsPage = lazy(() => import("./AnnouncementsPage"));
const InventoryPage = lazy(() => import("./StockPages").then((module) => ({ default: module.InventoryPage })));
const StockRequestsPage = lazy(() => import("./StockPages").then((module) => ({ default: module.StockRequestsPage })));
const SubmitFeedbackPage = lazy(() => import("./FeedbackPages").then((module) => ({ default: module.SubmitFeedbackPage })));
const FeedbackInboxPage = lazy(() => import("./FeedbackPages").then((module) => ({ default: module.FeedbackInboxPage })));
const NoticesPage = lazy(() => import("./NoticesPage"));
const LabsPage = lazy(() => import("./DetailsPages").then((module) => ({ default: module.LabsPage })));
const DepartmentDetailsPage = lazy(() => import("./DetailsPages").then((module) => ({ default: module.DepartmentDetailsPage })));
const TimetablePage = lazy(() => import("./TimetablePage"));

const pages: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: (
    <RequireDepartmentPermission permission="department.announcement.view">
      <AnnouncementsPage />
    </RequireDepartmentPermission>
  ) },
  { path: "inventory", element: (
    <RequireDepartmentPermission permission="department.stock.view"><InventoryPage /></RequireDepartmentPermission>
  ) },
  { path: "stock-requests", element: (
    <RequireDepartmentPermission permission="department.stock_request.view"><StockRequestsPage /></RequireDepartmentPermission>
  ) },
  { path: "feedback", element: (
    <RequireDepartmentPermission permission="department.feedback.create"><SubmitFeedbackPage /></RequireDepartmentPermission>
  ) },
  { path: "feedback-inbox", element: (
    <RequireDepartmentPermission permission="department.feedback.view"><FeedbackInboxPage /></RequireDepartmentPermission>
  ) },
  { path: "notices", element: (
    <RequireDepartmentPermission permission="department.notice.view"><NoticesPage /></RequireDepartmentPermission>
  ) },
  { path: "labs", element: (
    <RequireDepartmentPermission permission="department.lab.view"><LabsPage /></RequireDepartmentPermission>
  ) },
  { path: "timetable", element: (
    <RequireDepartmentPermission permission="department.timetable.view"><TimetablePage /></RequireDepartmentPermission>
  ) },
  { path: "details", element: (
    <RequireDepartmentPermission permission="department.details.view"><DepartmentDetailsPage /></RequireDepartmentPermission>
  ) },
];

export const routes: RouteObject[] = [{ element: <DepartmentLayout />, children: pages }];
