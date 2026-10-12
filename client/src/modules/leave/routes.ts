import { lazy } from 'react';

const LeaveDashboard = lazy(() => import('./components/LeaveDashboard'));

export const leaveRoutes = [
  {
    path: '/leave',
    element: LeaveDashboard,
  },
];