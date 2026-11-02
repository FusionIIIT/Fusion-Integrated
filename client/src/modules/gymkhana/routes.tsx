import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const GymkhanaPage = lazy(() => import("./pages/GymkhanaPage"));

export const routes: RouteObject[] = [
  { index: true, element: <GymkhanaPage /> },
];
