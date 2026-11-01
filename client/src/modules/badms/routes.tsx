import type { RouteObject } from "react-router-dom";

import SecureArchivalPage from "./SecureArchivalPage";

export const routes: RouteObject[] = [
  { index: true, element: <SecureArchivalPage /> },
  { path: "archival", element: <SecureArchivalPage /> },
];
