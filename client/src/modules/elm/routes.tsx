import { Navigate, type RouteObject } from "react-router-dom";

import RequestsPage from "./pages/RequestsPage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <RequestsPage /> },
];
