import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ArchivesPage = lazy(() => import("./pages/ArchivesPage"));
const HodReviewPage = lazy(() => import("./pages/HodReviewPage"));
const ClassificationPage = lazy(() => import("./pages/ClassificationPage"));
const SecurityPage = lazy(() => import("./pages/SecurityPage"));
const BackupsPage = lazy(() => import("./pages/BackupsPage"));
const RestorationsPage = lazy(() => import("./pages/RestorationsPage"));
const StoragePage = lazy(() => import("./pages/StoragePage"));
const AuditReportsPage = lazy(() => import("./pages/AuditReportsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="archives" replace /> },
  { path: "archives", element: <ArchivesPage /> },
  { path: "hod-review", element: <HodReviewPage /> },
  { path: "classification", element: <ClassificationPage /> },
  { path: "security", element: <SecurityPage /> },
  { path: "backups", element: <BackupsPage /> },
  { path: "restorations", element: <RestorationsPage /> },
  { path: "storage", element: <StoragePage /> },
  { path: "audit-reports", element: <AuditReportsPage /> },
];
