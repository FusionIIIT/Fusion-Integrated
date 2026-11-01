import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MinePage = lazy(() => import("./pages/MinePage"));
const SubstitutionsPage = lazy(() => import("./pages/SubstitutionsPage"));
const InboxPage = lazy(() => import("./pages/InboxPage"));
const TeamPage = lazy(() => import("./pages/TeamPage"));
const AdministrationPage = lazy(() => import("./pages/AdministrationPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <MinePage /> },
  { path: "substitutions", element: <SubstitutionsPage /> },
  { path: "inbox", element: <InboxPage /> },
  { path: "team", element: <TeamPage /> },
  { path: "administration", element: <AdministrationPage /> },
];
