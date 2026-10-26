import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal. */
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const InboxPage = lazy(() => import("./pages/InboxPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MyLeavePage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "inbox", element: <InboxPage /> },
  { path: "admin", element: <AdminPage /> },
];
