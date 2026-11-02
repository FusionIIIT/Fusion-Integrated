import { Navigate, type RouteObject } from "react-router-dom";

import PurchaseStoresPage from "./PurchaseStoresPage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="indents" replace /> },
  { path: "indents", element: <PurchaseStoresPage area="indents" /> },
  { path: "stock", element: <PurchaseStoresPage area="stock" /> },
  { path: "procurement", element: <PurchaseStoresPage area="procurement" /> },
];
