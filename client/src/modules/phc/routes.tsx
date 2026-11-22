import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const PatientDashboardPage = lazy(() => import("./pages/PatientDashboardPage"));
const DoctorAvailabilityPage = lazy(() => import("./pages/DoctorAvailabilityPage"));
const MedicalRecordsPage = lazy(() => import("./pages/MedicalRecordsPage"));
const ReimbursementsPage = lazy(() => import("./pages/ReimbursementsPage"));
const VisitsPage = lazy(() => import("./pages/VisitsPage"));
const SchedulesPage = lazy(() => import("./pages/SchedulesPage"));
const AttendancePage = lazy(() => import("./pages/AttendancePage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const RequisitionsPage = lazy(() => import("./pages/RequisitionsPage"));
const AmbulancePage = lazy(() => import("./pages/AmbulancePage"));
const AdvisoriesPage = lazy(() => import("./pages/AdvisoriesPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="patient-dashboard" replace /> },
  { path: "patient-dashboard", element: guarded("phc.patient_record.view", <PatientDashboardPage />) },
  { path: "doctor-availability", element: guarded("phc.doctor_schedule.view", <DoctorAvailabilityPage />) },
  { path: "medical-records", element: guarded("phc.patient_record.view", <MedicalRecordsPage />) },
  { path: "reimbursements", element: guarded("phc.reimbursement.view", <ReimbursementsPage />) },
  { path: "staff/visits", element: guarded("phc.patient_record.create", <VisitsPage />) },
  { path: "staff/schedules", element: guarded("phc.doctor_schedule.update", <SchedulesPage />) },
  { path: "staff/attendance", element: guarded("phc.doctor_attendance.update", <AttendancePage />) },
  { path: "staff/inventory", element: guarded("phc.inventory.view", <InventoryPage />) },
  { path: "staff/requisitions", element: guarded("phc.requisition.view", <RequisitionsPage />) },
  { path: "staff/ambulance", element: guarded("phc.ambulance_usage.view", <AmbulancePage />) },
  { path: "advisories", element: guarded("phc.advisory.view", <AdvisoriesPage />) },
  { path: "staff/advisories", element: guarded("phc.advisory.publish", <AdvisoriesPage />) },
  { path: "staff/reports", element: guarded("phc.report.view", <ReportsPage />) },
  { path: "notifications", element: guarded("phc.notification.view", <NotificationsPage />) },
  { path: "accounts/claims", element: guarded("phc.reimbursement.manage", <ReimbursementsPage />) },
  { path: "authority/claims", element: guarded("phc.reimbursement.approve", <ReimbursementsPage />) },
  { path: "authority/requisitions", element: guarded("phc.requisition.approve", <RequisitionsPage />) },
];
