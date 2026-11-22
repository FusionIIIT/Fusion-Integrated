import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const DoctorAvailabilityPage = lazy(() => import("./pages/DoctorAvailabilityPage"));
const MedicalHistoryPage = lazy(() => import("./pages/MedicalHistoryPage"));
const HealthAnnouncementsPage = lazy(() => import("./pages/HealthAnnouncementsPage"));
const ReimbursementApplyPage = lazy(() => import("./pages/ReimbursementApplyPage"));
const ReimbursementTrackingPage = lazy(() => import("./pages/ReimbursementTrackingPage"));
const PatientVisitsManagementPage = lazy(() => import("./pages/PatientVisitsManagementPage"));
const InventoryStockPage = lazy(() => import("./pages/InventoryStockPage"));
const ProcurementRequisitionsPage = lazy(() => import("./pages/ProcurementRequisitionsPage"));
const AmbulanceLogsPage = lazy(() => import("./pages/AmbulanceLogsPage"));
const ReimbursementReviewPage = lazy(() => import("./pages/ReimbursementReviewPage"));
const PHCReportsPage = lazy(() => import("./pages/PHCReportsPage"));
const PHCAuditTrailPage = lazy(() => import("./pages/PHCAuditTrailPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="doctor-schedule" replace /> },
  { path: "doctor-schedule", element: <DoctorAvailabilityPage /> },
  { path: "my-medical-history", element: <MedicalHistoryPage /> },
  { path: "announcements", element: <HealthAnnouncementsPage /> },
  { path: "reimbursement/apply", element: <ReimbursementApplyPage /> },
  { path: "reimbursement/tracking", element: <ReimbursementTrackingPage /> },
  { path: "patient-records", element: <PatientVisitsManagementPage /> },
  { path: "inventory", element: <InventoryStockPage /> },
  { path: "requisitions", element: <ProcurementRequisitionsPage /> },
  { path: "ambulance", element: <AmbulanceLogsPage /> },
  { path: "reimbursement/queue", element: <ReimbursementReviewPage /> },
  { path: "reports", element: <PHCReportsPage /> },
  { path: "audit", element: <PHCAuditTrailPage /> },
];
