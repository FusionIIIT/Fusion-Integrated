import React from "react";
import { RouteObject } from "react-router-dom";
import VmsPage from "./VmsPage";

const routes: RouteObject[] = [
  {
    path: "",
    element: <VmsPage />,
  },
  {
    path: "register",
    element: <VmsPage />,
  },
  {
    path: "approvals",
    element: <VmsPage />,
  },
  {
    path: "gate",
    element: <VmsPage />,
  },
  {
    path: "passes",
    element: <VmsPage />,
  },
];

export default routes;
