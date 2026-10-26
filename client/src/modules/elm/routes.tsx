import React from 'react';
import { Route, Routes } from 'react-router-dom';
import ApplyLeavePage from './pages/ApplyLeavePage';
import LeaveHistoryPage from './pages/LeaveHistoryPage';

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="apply" element={<ApplyLeavePage />} />
      <Route path="history" element={<LeaveHistoryPage />} />
    </Routes>
  );
};

export default AppRoutes;