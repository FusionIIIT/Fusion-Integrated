import { Navigate, type RouteObject } from "react-router-dom";

import ElmMinePage from "./pages/ElmMinePage";
import ElmQueuePage from "./pages/ElmQueuePage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <ElmMinePage /> },
  { path: "queue", element: <ElmQueuePage /> },
];
