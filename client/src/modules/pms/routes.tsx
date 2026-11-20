import { lazy, type ReactNode } from "react";
import { Container } from "@mantine/core";
import { Navigate, type RouteObject } from "react-router-dom";

import { useAuth } from "../../auth/AuthProvider";
import { RequirePermission } from "../../auth/RequirePermission";
import { NotPermitted } from "../../ui/components/NotPermitted";

const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const SubmitApplicationPage = lazy(() => import("./pages/SubmitApplicationPage"));
const ApplicationQueuePage = lazy(() => import("./pages/ApplicationQueuePage"));
const ReviewsPage = lazy(() => import("./pages/ReviewsPage"));
const FilingsPage = lazy(() => import("./pages/FilingsPage"));
const OfficeActionsPage = lazy(() => import("./pages/OfficeActionsPage"));
const MaintenancePage = lazy(() => import("./pages/MaintenancePage"));
const LicensingPage = lazy(() => import("./pages/LicensingPage"));

function AnyPermission({ permissions, children }: { permissions: string[]; children: ReactNode }) {
  const { can } = useAuth();
  return permissions.some(can)
    ? <>{children}</>
    : <Container size="xl" pt="md"><NotPermitted /></Container>;
}

function any(permissions: string[], page: ReactNode) {
  return <AnyPermission permissions={permissions}>{page}</AnyPermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <RequirePermission permission="pms.application.view_self"><MyApplicationsPage /></RequirePermission> },
  { path: "submit", element: <RequirePermission permission="pms.application.create"><SubmitApplicationPage /></RequirePermission> },
  { path: "queue", element: <RequirePermission permission="pms.application.view"><ApplicationQueuePage /></RequirePermission> },
  { path: "reviews", element: any(["pms.application.review", "pms.budget.review", "pms.application.review_appeal", "pms.licensing.review"], <ReviewsPage />) },
  { path: "filings", element: any(["pms.attorney.respond_assignment", "pms.patentability.assess", "pms.advice.record", "pms.filing.record"], <FilingsPage />) },
  { path: "office-actions", element: any(["pms.office_action.record", "pms.office_action.respond", "pms.office_action.review"], <OfficeActionsPage />) },
  { path: "maintenance", element: any(["pms.maintenance.manage", "pms.maintenance.decide"], <MaintenancePage />) },
  { path: "licensing", element: any(["pms.licensing.submit", "pms.licensing.review"], <LicensingPage />) },
];
