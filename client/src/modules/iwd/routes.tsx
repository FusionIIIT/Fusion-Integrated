import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const IwdPage = lazy(() => import("./pages/IwdPage"));

export const routes: RouteObject[] = [
  { index: true, element: <IwdPage /> },
  { path: "tasks", element: <IwdPage tasksOnly /> },
];
