import type { RouteObject } from "react-router-dom";
import ELMOverviewPage from "./pages/ELMOverviewPage";

export const routes: RouteObject[] = [
  { index: true, element: <ELMOverviewPage /> },
];
