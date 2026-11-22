import type { RouteObject } from "react-router-dom";

import ArchivesPage from "./pages/ArchivesPage";
import OperationsPage from "./pages/OperationsPage";
import OverviewPage from "./pages/OverviewPage";

export const routes: RouteObject[] = [
  { index: true, element: <OverviewPage /> },
  { path: "archives", element: <ArchivesPage /> },
  { path: "operations", element: <OperationsPage /> },
];
