import React, { lazy } from 'react';
import { RouteObject } from 'react-router-dom';

const StudentDashboardPage = lazy(() => import('./pages/StudentDashboardPage'));
const CaretakerReviewPage = lazy(() => import('./pages/CaretakerReviewPage'));
const MenuPage = lazy(() => import('./pages/MenuPage'));

export const mmsRoutes: RouteObject[] = [
  { path: 'dashboard', element: <StudentDashboardPage /> },
  { path: 'review', element: <CaretakerReviewPage /> },
  { path: 'menu', element: <MenuPage /> },
];