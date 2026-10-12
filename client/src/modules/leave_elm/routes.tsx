import { lazy } from 'react';
import { Navigate, type RouteObject } from 'react-router-dom';

const MyLeavePage = lazy(() => import('./pages/MyLeavePage'));
const LeaveTasksPage = lazy(() => import('./pages/LeaveTasksPage'));
const LeaveAdminPage = lazy(() => import('./pages/LeaveAdminPage'));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to='mine' replace /> },
  { path: 'mine', element: <MyLeavePage /> },
  { path: 'queue', element: <LeaveTasksPage /> },
  { path: 'admin', element: <LeaveAdminPage /> },
];
