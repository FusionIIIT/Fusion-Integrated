import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const DirectoryPage = lazy(() => import("./pages/DirectoryPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="profile" replace /> },
  { path: "profile", element: <ProfilePage /> },
  { path: "directory", element: <DirectoryPage /> },
];
