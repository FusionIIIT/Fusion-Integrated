import { lazy } from 'react';
import { Navigate, type RouteObject } from 'react-router-dom';
const OapDashboardPage = lazy(() => import('./pages/OapDashboardPage'));
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <OapDashboardPage /> },
  { path: "leave", element: <OapDashboardPage /> },
  { path: "bonafide", element: <OapDashboardPage /> },
  { path: "nodues", element: <OapDashboardPage /> },
  { path: "assistantship", element: <OapDashboardPage /> },
  { path: "seminar", element: <OapDashboardPage /> },
];