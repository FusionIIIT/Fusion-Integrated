import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const DoctorSchedulePage = lazy(() => import("./pages/DoctorSchedulePage"));
const MyRecordsPage = lazy(() => import("./pages/MyRecordsPage"));
const ManageSchedulePage = lazy(() => import("./pages/ManageSchedulePage"));
const RecordVisitPage = lazy(() => import("./pages/RecordVisitPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="doctor-schedule" replace /> },
  { path: "records", element: <MyRecordsPage /> },
  { path: "manage-schedule", element: <ManageSchedulePage /> },
  { path: "visits", element: <RecordVisitPage /> },
];
