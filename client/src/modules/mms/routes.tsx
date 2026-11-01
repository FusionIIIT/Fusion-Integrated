import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const MenuPage = lazy(() => import("./pages/MenuPage").then((m) => ({ default: m.MenuPage })));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage").then((m) => ({ default: m.RegistrationPage })));
const RebatesPage = lazy(() => import("./pages/RebatesPage").then((m) => ({ default: m.RebatesPage })));
const CaretakerPage = lazy(() => import("./pages/CaretakerPage").then((m) => ({ default: m.CaretakerPage })));
const AdminPage = lazy(() => import("./pages/AdminPage").then((m) => ({ default: m.AdminPage })));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <DashboardPage /> },
  { path: "menu", element: <MenuPage /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "rebates", element: <RebatesPage /> },
  { path: "caretaker", element: <CaretakerPage /> },
  { path: "admin", element: <AdminPage /> },
];
