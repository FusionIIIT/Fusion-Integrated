import type { RouteObject } from "react-router-dom";
import { IwdDashboard } from "./index";

export const routes: RouteObject[] = [
  {
    path: "",
    element: <IwdDashboard />,
  },
];
