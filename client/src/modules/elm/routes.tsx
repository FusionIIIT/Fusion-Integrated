import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));

export const routes: RouteObject[] = [
  { path: "my-leave", element: <MyLeavePage /> },
];

