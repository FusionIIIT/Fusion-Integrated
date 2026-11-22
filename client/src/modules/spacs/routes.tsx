import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const CataloguePage = lazy(() => import("./pages/CataloguePage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const AwardResultsPage = lazy(() => import("./pages/AwardResultsPage"));
const VerificationQueuePage = lazy(() => import("./pages/VerificationQueuePage"));
const DecisionQueuePage = lazy(() => import("./pages/DecisionQueuePage"));
const CatalogueAdminPage = lazy(() => import("./pages/CatalogueAdminPage"));
const AwardManagementPage = lazy(() => import("./pages/AwardManagementPage"));
const AuditTrailPage = lazy(() => import("./pages/AuditTrailPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="catalogue" replace /> },
  { path: "catalogue", element: <CataloguePage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "awards", element: <AwardResultsPage /> },
  { path: "verification-queue", element: <VerificationQueuePage /> },
  { path: "decision-queue", element: <DecisionQueuePage /> },
  { path: "catalogue-admin", element: <CatalogueAdminPage /> },
  { path: "award-management", element: <AwardManagementPage /> },
  { path: "audit-trail", element: <AuditTrailPage /> },
];
