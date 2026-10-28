import { Navigate, type RouteObject } from "react-router-dom";
import { ElmPage } from "./pages/ElmPage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <ElmPage /> },
  { path: "tasks", element: <ElmPage tasks /> },
  { path: "policy", element: <ElmPage policy /> },
];
