import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const LeaveApplicationsPage = lazy(
  () => import("./pages/LeaveApplicationsPage").then(
    ({ LeaveApplicationsPage: Page }) => ({ default: Page }),
  ));
const LeaveBalancePage = lazy(
  () => import("./pages/LeaveBalancePage").then(
    ({ LeaveBalancePage: Page }) => ({ default: Page }),
  ));
const LeaveRequestPage = lazy(
  () => import("./pages/LeaveRequestPage").then(
    ({ LeaveRequestPage: Page }) => ({ default: Page }),
  ));
const LeaveHistoryPage = lazy(
  () => import("./pages/LeaveHistoryPage").then(
    ({ LeaveHistoryPage: Page }) => ({ default: Page }),
  ));
const LeavePrintPage = lazy(
  () => import("./pages/LeavePrintPage").then(
    ({ LeavePrintPage: Page }) => ({ default: Page }),
  ));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-applications" replace /> },
  { path: "my-applications", element: <LeaveApplicationsPage /> },
  { path: "my-balance", element: <LeaveBalancePage /> },
  { path: "request-leave", element: <LeaveRequestPage /> },
  { path: "leave-history", element: <LeaveHistoryPage /> },
  { path: "print-application/:applicationId", element: <LeavePrintPage /> },
];
