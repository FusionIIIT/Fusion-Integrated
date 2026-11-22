import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const Dashboard = lazy(() => import("./pages/Dashboard"));

export const routes: RouteObject[] = [{ index: true, element: <Dashboard /> }];
