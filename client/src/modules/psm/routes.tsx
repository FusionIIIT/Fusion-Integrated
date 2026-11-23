import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const StockItemsPage = lazy(() => import("./pages/StockItemsPage"));
const IndentsPage = lazy(() => import("./pages/IndentsPage"));
const IndentItemsPage = lazy(() => import("./pages/IndentItemsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="indents" replace /> },
  { path: "indents", element: <IndentsPage /> },
  { path: "stock", element: <StockItemsPage /> },
  { path: "indents/:indent_id/items", element: <IndentItemsPage /> },
];

export default routes;
