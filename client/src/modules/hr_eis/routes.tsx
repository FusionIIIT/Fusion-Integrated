import React, { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const EmployeeProfilePage = lazy(() => import("./pages/EmployeeProfilePage"));
const LeaveManagementPage = lazy(() => import("./pages/LeaveManagementPage"));
const AppraisalPage = lazy(() => import("./pages/AppraisalPage"));
const LtcClaimsPage = lazy(() => import("./pages/LtcClaimsPage"));
const CpdaClaimsPage = lazy(() => import("./pages/CpdaClaimsPage"));
const AdminDashboardPage = lazy(() => import("./pages/AdminDashboardPage"));

export const routes: RouteObject[] = [
  { path: "", element: <EmployeeProfilePage /> },
  { path: "profile", element: <EmployeeProfilePage /> },
  { path: "leave", element: <LeaveManagementPage /> },
  { path: "appraisal", element: <AppraisalPage /> },
  { path: "ltc", element: <LtcClaimsPage /> },
  { path: "cpda", element: <CpdaClaimsPage /> },
  { path: "admin", element: <AdminDashboardPage /> },
  { path: "approvals", element: <AdminDashboardPage /> },
];

export default routes;
