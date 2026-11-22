import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page: the import() argument must be a static literal. */
const SchedulePage = lazy(() => import("./pages/SchedulePage"));
const MyRecordsPage = lazy(() => import("./pages/MyRecordsPage"));
const MyClaimsPage = lazy(() => import("./pages/MyClaimsPage"));
const AdvisoriesPage = lazy(() => import("./pages/AdvisoriesPage"));
const StaffSchedulePage = lazy(() => import("./pages/StaffSchedulePage"));
const AttendancePage = lazy(() => import("./pages/AttendancePage"));
const PatientRecordsPage = lazy(() => import("./pages/PatientRecordsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const RequisitionsPage = lazy(() => import("./pages/RequisitionsPage"));
const AmbulancePage = lazy(() => import("./pages/AmbulancePage"));
const AdvisoryManagePage = lazy(() => import("./pages/AdvisoryManagePage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const AuditVerifyPage = lazy(() => import("./pages/AuditVerifyPage"));
const AuditPaymentsPage = lazy(() => import("./pages/AuditPaymentsPage"));
const ApproverRequisitionsPage = lazy(
  () => import("./pages/ApproverRequisitionsPage"));
const ApproverSanctionsPage = lazy(
  () => import("./pages/ApproverSanctionsPage"));

/** Paths are relative: the shell mounts them under /phc from the manifest. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="schedule" replace /> },
  { path: "schedule", element: <SchedulePage /> },
  { path: "records", element: <MyRecordsPage /> },
  { path: "claims", element: <MyClaimsPage /> },
  { path: "advisories", element: <AdvisoriesPage /> },
  { path: "staff/schedule", element: <StaffSchedulePage /> },
  { path: "staff/attendance", element: <AttendancePage /> },
  { path: "staff/patients", element: <PatientRecordsPage /> },
  { path: "staff/inventory", element: <InventoryPage /> },
  { path: "staff/requisitions", element: <RequisitionsPage /> },
  { path: "staff/ambulance", element: <AmbulancePage /> },
  { path: "staff/advisories", element: <AdvisoryManagePage /> },
  { path: "staff/reports", element: <ReportsPage /> },
  { path: "audit/claims", element: <AuditVerifyPage /> },
  { path: "audit/payments", element: <AuditPaymentsPage /> },
  { path: "approver/requisitions", element: <ApproverRequisitionsPage /> },
  { path: "approver/sanctions", element: <ApproverSanctionsPage /> },
];
