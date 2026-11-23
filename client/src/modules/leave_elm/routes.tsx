import type { RouteObject } from 'react-router-dom';
import Mine from './pages/MyLeavePage';
import LeaveTasksPage from './pages/LeaveTasksPage';
import LeaveAdminPage from './pages/LeaveAdminPage';

export const routes: RouteObject[] = [
  {
    path: "mine",
    element: <Mine />,
  },
  {
    path: "queue",
    element: <LeaveTasksPage />,
  },
  {
    path: "admin",
    element: <LeaveAdminPage />,
  },
];
