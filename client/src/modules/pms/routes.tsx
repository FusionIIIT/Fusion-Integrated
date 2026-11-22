import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite splits these via static import() literals. */
const PMSDashboardPage = lazy(() => import("./pages/PMSDashboardPage"));
const NewApplicationPage = lazy(() => import("./pages/NewApplicationPage"));
const ApplicationDetailPage = lazy(() => import("./pages/ApplicationDetailPage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const OfficeActionsPage = lazy(() => import("./pages/OfficeActionsPage"));
const MaintenancePage = lazy(() => import("./pages/MaintenancePage"));
const FinanceLedgerPage = lazy(() => import("./pages/FinanceLedgerPage"));

/** Paths are RELATIVE — mounted under /pms by the shell manifest. */
export const routes: RouteObject[] = [
  { index: true, element: <PMSDashboardPage /> },
  { path: "applications/new", element: <NewApplicationPage /> },
  { path: "applications/:id", element: <ApplicationDetailPage /> },
  { path: "reviews", element: <ReviewsPage /> },
  { path: "office-actions", element: <OfficeActionsPage /> },
  { path: "maintenance", element: <MaintenancePage /> },
  { path: "finance", element: <FinanceLedgerPage /> },
  { path: "*", element: <Navigate to="" replace /> },
];
