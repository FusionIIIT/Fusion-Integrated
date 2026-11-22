import type { RouteObject } from "react-router-dom";
import { ComplaintsPage } from "./pages/ComplaintsPage";

export const routes: RouteObject[] = [
  {
    path: "complaints",
    element: <ComplaintsPage />,
  },
];
