import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const ComplaintsListPage = lazy(() => import("./pages/ComplaintsListPage"));
const ComplaintSubmitPage = lazy(() => import("./pages/ComplaintSubmitPage"));
const ComplaintDetailPage = lazy(() => import("./pages/ComplaintDetailPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const BillingPage = lazy(() => import("./pages/BillingPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="complaints" replace /> },
  {
    path: "complaints",
    element: guarded("iwd.complaint.view", <ComplaintsListPage />),
  },
  {
    path: "submit",
    element: guarded("iwd.complaint.create", <ComplaintSubmitPage />),
  },
  {
    path: "approvals",
    element: guarded("iwd.estimate.review", <ApprovalsPage />),
  },
  {
    path: "inventory",
    element: guarded("iwd.inventory.manage", <InventoryPage />),
  },
  {
    path: "billing",
    element: guarded("iwd.bill.review", <BillingPage />),
  },
];
