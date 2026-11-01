import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
const MyLeavePage = lazy(() => import("./pages/MyLeavePage"));
export const routes: RouteObject[] = [
 { index:true, element:<Navigate to="my-leave" replace/> },
 { path:"my-leave", element:<MyLeavePage/> },
 { path:"apply", element:<MyLeavePage/> },
 { path:"approvals", element:<MyLeavePage/> },
 { path:"substitute-requests", element:<MyLeavePage/> },
 { path:"admin", element:<MyLeavePage/> },
];
