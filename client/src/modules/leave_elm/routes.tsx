import { type RouteObject } from "react-router-dom";

import LeaveHome from "./pages/LeaveHome";

export const routes: RouteObject[] = [
  { path: "my-leave", element: <LeaveHome /> },
];
