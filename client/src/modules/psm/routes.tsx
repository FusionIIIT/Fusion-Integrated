import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const IndentsPage = lazy(() => import("./pages/IndentsPage"));
const VendorsPage = lazy(() => import("./pages/VendorsPage"));
const PurchaseOrdersPage = lazy(() => import("./pages/PurchaseOrdersPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath (/psm).
 *  Matches NAV_ITEMS in modules/psm/registry.py.
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="indents" replace /> },
  { path: "indents", element: <IndentsPage /> },
  { path: "vendors", element: <VendorsPage /> },
  { path: "purchase-orders", element: <PurchaseOrdersPage /> },
];
