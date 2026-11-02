import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const FeedbackPage = lazy(() => import("./pages/FeedbackPage"));
const ResourcesPage = lazy(() => import("./pages/ResourcesPage"));
const AcademicInfoPage = lazy(() => import("./pages/AcademicInfoPage"));
const DepartmentDetailsPage = lazy(() => import("./pages/DepartmentDetailsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="announcements" replace /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "inventory", element: <InventoryPage /> },
  { path: "feedback", element: <FeedbackPage /> },
  { path: "resources", element: <ResourcesPage /> },
  { path: "details", element: <DepartmentDetailsPage /> },
  { path: "academics", element: <AcademicInfoPage /> },
];
