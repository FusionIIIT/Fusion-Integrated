/**
 * ELM Frontend Routes.
 * Mechanically adapted for RouteObject[] interface expected by Fusion MODULE_REGISTRY.
 */

import React from "react";
import type { RouteObject } from "react-router-dom";
import LeaveBalance from "./LeaveBalance";
import LeaveApplication from "./LeaveApplication";

export const routes: RouteObject[] = [
  {
    path: "",
    element: <LeaveBalance />,
  },
  {
    path: "apply",
    element: <LeaveApplication />,
  },
];

export default routes;
