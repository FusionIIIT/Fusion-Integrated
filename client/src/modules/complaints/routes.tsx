import type { RouteObject } from "react-router-dom";
import { ComplaintSubmitPage } from "./pages/ComplaintSubmitPage";

export const routes: RouteObject[] = [
  { path: "submit", element: <ComplaintSubmitPage /> },
];
