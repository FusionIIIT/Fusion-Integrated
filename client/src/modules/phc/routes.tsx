import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const SchedulePage = lazy(() => import("./pages/SchedulePage"));
const AdvisoriesPage = lazy(() => import("./pages/AdvisoriesPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const ClaimsPage = lazy(() => import("./pages/ClaimsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const RequisitionsPage = lazy(() => import("./pages/RequisitionsPage"));
const AmbulancePage = lazy(() => import("./pages/AmbulancePage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));

// Each page opens only for its nav item's required_permission (registry.py).
function guard(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="schedule" replace /> },
  { path: "schedule", element: guard("phc.schedule.view", <SchedulePage />) },
  { path: "advisories", element: guard("phc.advisory.view", <AdvisoriesPage />) },
  { path: "records", element: guard("phc.record.view", <RecordsPage />) },
  { path: "claims", element: guard("phc.claim.view", <ClaimsPage />) },
  { path: "inventory", element: guard("phc.inventory.view", <InventoryPage />) },
  { path: "requisitions", element: guard("phc.requisition.view", <RequisitionsPage />) },
  { path: "ambulance", element: guard("phc.ambulance.view", <AmbulancePage />) },
  { path: "reports", element: guard("phc.report.view", <ReportsPage />) },
  { path: "notifications", element: guard("phc.notification.view", <NotificationsPage />) },
];
