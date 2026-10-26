import React from 'react';
import { Route, Routes } from 'react-router-dom';
import LeaveRequestList from './LeaveRequestList';
import LeaveRequestDetail from './LeaveRequestDetail';

const routes: RouteObject[] = [
  {
    path: '/leave-requests',
    element: <LeaveRequestList />,
  },
  {
    path: '/leave-requests/:id',
    element: <LeaveRequestDetail />,
  },
];

export default routes;
