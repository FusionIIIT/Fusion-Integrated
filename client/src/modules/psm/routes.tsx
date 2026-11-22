// Lazy route table matching modules/psm/registry.py NAV_ITEMS 1:1.
import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const IndentsPage = lazy(() => import("./pages/IndentsPage"));
const StockPage = lazy(() => import("./pages/StockPage"));
const TransfersPage = lazy(() => import("./pages/TransfersPage"));
const VendorsPage = lazy(() => import("./pages/VendorsPage"));
const TendersPage = lazy(() => import("./pages/TendersPage"));
const PurchaseOrdersPage = lazy(() => import("./pages/PurchaseOrdersPage"));
const ReceiptsPage = lazy(() => import("./pages/ReceiptsPage"));
const InvoicesPage = lazy(() => import("./pages/InvoicesPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AuditPage = lazy(() => import("./pages/AuditPage"));
const PolicyPage = lazy(() => import("./pages/PolicyPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "indents", element: <IndentsPage /> },
  { path: "stock", element: office("psm.stock.view", <StockPage />) },
  { path: "transfers", element: office("psm.transfer.view", <TransfersPage />) },
  { path: "vendors", element: office("psm.vendor.view", <VendorsPage />) },
  { path: "tenders", element: office("psm.tender.view", <TendersPage />) },
  { path: "purchase-orders", element: office("psm.purchase_order.view", <PurchaseOrdersPage />) },
  { path: "receipts", element: <ReceiptsPage /> },
  { path: "invoices", element: office("psm.invoice.view", <InvoicesPage />) },
  { path: "reports", element: office("psm.report.view", <ReportsPage />) },
  { path: "audit", element: office("psm.audit.view", <AuditPage />) },
  { path: "policy", element: office("psm.policy.view", <PolicyPage />) },
];
