import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const ApplyPage = lazy(() => import("./pages/ApplyPage"));
const MyRequestsPage = lazy(() => import("./pages/MyRequestsPage"));
const BalancesPage = lazy(() => import("./pages/BalancesPage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const ExceptionsPage = lazy(() => import("./pages/ExceptionsPage"));
const AdminPage = lazy(() => import("./pages/AdminPage"));
const AccountsPage = lazy(() => import("./pages/AccountsPage"));
const CalendarPage = lazy(() => import("./pages/CalendarPage"));
const YearEndPage = lazy(() => import("./pages/YearEndPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "apply", element: <ApplyPage /> },
  { path: "requests", element: <MyRequestsPage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "exceptions", element: <ExceptionsPage /> },
  { path: "admin", element: <AdminPage /> },
  { path: "admin/calendar", element: <CalendarPage /> },
  { path: "admin/year-end", element: <YearEndPage /> },
  { path: "accounts", element: <AccountsPage /> },
];