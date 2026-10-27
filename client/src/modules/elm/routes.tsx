import type { RouteObject } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';

export const routes: RouteObject[] = [
  {
    path: '',
    element: <DashboardPage />,
  },
  {
    path: 'apply',
    element: <DashboardPage />,
  },
  {
    path: 'mine',
    element: <DashboardPage />,
  },
  {
    path: 'substitute',
    element: <DashboardPage />,
  },
  {
    path: 'approvals',
    element: <DashboardPage />,
  },
  {
    path: 'balances',
    element: <DashboardPage />,
  },
  {
    path: 'admin',
    element: <DashboardPage />,
  },
];
