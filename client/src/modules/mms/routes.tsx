import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const MessDashboardPage = lazy(() => import("./pages/MessDashboardPage"));
const MenuPage = lazy(() => import("./pages/MenuPage"));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage"));
const RebatesPage = lazy(() => import("./pages/RebatesPage"));

export const routes: RouteObject[] = [
  { index: true, element: <MessDashboardPage /> },
  { path: "menu", element: <MenuPage /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "rebates", element: <RebatesPage /> },
];

