import { lazy } from 'react';
import { Navigate, type RouteObject } from 'react-router-dom';

const Courses = lazy(() => import('./pages').then((m) => ({default:m.Courses})));
const Workspace = lazy(() => import('./pages').then((m) => ({default:m.Workspace})));
export const routes: RouteObject[] = [
  {index:true, element:<Navigate to="courses" replace />},
  {path:"courses", element:<Courses />},
  {path:"courses/:id", element:<Workspace />},
];
