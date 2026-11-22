import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const IndentsPage = lazy(() => import("./pages/IndentsPage"));
const IndentCreatePage = lazy(() => import("./pages/IndentCreatePage"));
const ApprovalQueuePage = lazy(() => import("./pages/ApprovalQueuePage"));
const PurchaseOrdersPage = lazy(() => import("./pages/PurchaseOrdersPage"));
const GoodsReceiptsPage = lazy(() => import("./pages/GoodsReceiptsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const VendorsPage = lazy(() => import("./pages/VendorsPage"));
const DiscrepanciesPage = lazy(() => import("./pages/DiscrepanciesPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="indents" replace /> },
  { path: "indents", element: guarded("psm.indent.view", <IndentsPage />) },
  { path: "indents/new", element: guarded("psm.indent.create", <IndentCreatePage />) },
  { path: "approvals", element: guarded("psm.indent.approve_dept", <ApprovalQueuePage />) },
  { path: "purchase-orders", element: guarded("psm.po.view", <PurchaseOrdersPage />) },
  { path: "goods-receipts", element: guarded("psm.grn.view", <GoodsReceiptsPage />) },
  { path: "inventory", element: guarded("psm.stock.view", <InventoryPage />) },
  { path: "vendors", element: guarded("psm.vendor.view", <VendorsPage />) },
  { path: "discrepancies", element: guarded("psm.discrepancy.manage", <DiscrepanciesPage />) },
];
