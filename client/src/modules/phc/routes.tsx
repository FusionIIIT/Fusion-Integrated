import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const AppointmentsPage = lazy(() => import("./pages/AppointmentsPage"));
const PatientsPage = lazy(() => import("./pages/PatientsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ConsultationsPage = lazy(() => import("./pages/ConsultationsPage"));
const SchedulesPage = lazy(() => import("./pages/SchedulesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="appointments" replace /> },
  { path: "appointments", element: <AppointmentsPage /> },
  { path: "patients", element: <PatientsPage /> },
  { path: "inventory", element: <InventoryPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "consultations", element: <ConsultationsPage /> },
  { path: "schedules", element: <SchedulesPage /> },
];
