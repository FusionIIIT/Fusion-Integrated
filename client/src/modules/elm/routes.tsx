import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));

export const routes: RouteObject[] = [
  { path: "my-leave", element: <MyLeavePage /> },
];
