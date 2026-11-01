import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ProposalsPage = lazy(() => import("./pages/ProposalsPage"));
const ConsultancyPage = lazy(() => import("./pages/ConsultancyPage"));
const AppointmentsPage = lazy(() => import("./pages/AppointmentsPage"));
const FinancePage = lazy(() => import("./pages/FinancePage"));
const ProcurementPage = lazy(() => import("./pages/ProcurementPage"));
const ProgressReportsPage = lazy(() => import("./pages/ProgressReportsPage"));
const ClosuresPage = lazy(() => import("./pages/ClosuresPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="proposals" replace /> },
  { path: "proposals", element: <ProposalsPage /> },
  { path: "my-proposals", element: <ProposalsPage /> },
  { path: "consultancy", element: <ConsultancyPage /> },
  { path: "my-consultancy", element: <ConsultancyPage /> },
  { path: "appointments", element: <AppointmentsPage /> },
  { path: "finance", element: <FinancePage /> },
  { path: "my-finance", element: <FinancePage /> },
  { path: "procurement", element: <ProcurementPage /> },
  { path: "progress-reports", element: <ProgressReportsPage /> },
  { path: "my-progress-reports", element: <ProgressReportsPage /> },
  { path: "closures", element: <ClosuresPage /> },
  { path: "reports", element: <ReportsPage /> },
];
