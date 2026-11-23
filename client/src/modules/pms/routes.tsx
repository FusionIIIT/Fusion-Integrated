import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";
import { PmsGuard } from "./components/access";

// One lazy chunk per page; static import() literals so Vite can split them.
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const CasesPage = lazy(() => import("./pages/CasesPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const MonitoringPage = lazy(() => import("./pages/MonitoringPage"));
const OversightPage = lazy(() => import("./pages/OversightPage"));
const PriorArtPage = lazy(() => import("./pages/PriorArtPage"));
const LicensingPage = lazy(() => import("./pages/LicensingPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const DirectorsPage = lazy(() => import("./pages/DirectorsPage"));
const AttorneyPanelPage = lazy(() => import("./pages/AttorneyPanelPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));

// Each page opens only for its nav item's required_permission (registry.py), held by the acting role.
function guard(permission: string, page: ReactNode) {
  return (
    <RequirePermission permission={permission}>
      <PmsGuard permission={permission}>{page}</PmsGuard>
    </RequirePermission>
  );
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="applications" replace /> },
  { path: "applications", element: guard("pms.application.create", <ApplicationsPage />) },
  { path: "reviews", element: guard("pms.review.approve", <ReviewsPage />) },
  { path: "cases", element: guard("pms.attorney_assignment.review", <CasesPage />) },
  { path: "assignments", element: guard("pms.review.assign", <AssignmentsPage />) },
  { path: "monitoring", element: guard("pms.escalation.review", <MonitoringPage />) },
  { path: "oversight", element: guard("pms.workflow.view", <OversightPage />) },
  { path: "prior-art", element: guard("pms.prior_art.create", <PriorArtPage />) },
  { path: "licensing", element: guard("pms.licensing_request.view", <LicensingPage />) },
  { path: "reports", element: guard("pms.report.view", <ReportsPage />) },
  { path: "audit", element: guard("pms.audit_log.view", <AuditPage />) },
  { path: "directors", element: guard("pms.director_profile.update", <DirectorsPage />) },
  { path: "attorney-panel", element: guard("pms.attorney_panel.update", <AttorneyPanelPage />) },
  { path: "settings", element: guard("pms.policy.publish", <SettingsPage />) },
];
