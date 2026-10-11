import React from 'react';
import { Route } from 'react-router-dom';
import ApplyLeave from './pages/ApplyLeave';
import MyLeaves from './pages/MyLeaves';
import ApproveLeaves from './pages/ApproveLeaves';

const routes = [
  <Route path="/elm/apply" element={<ApplyLeave />} />,
  <Route path="/elm/my-leaves" element={<MyLeaves />} />,
  <Route path="/elm/approve-leaves" element={<ApproveLeaves />} />,
];

export default routes;