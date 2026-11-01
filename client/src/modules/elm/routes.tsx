import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
const Home=lazy(()=>import("./pages/ElmHomePage"));
const Apply=lazy(()=>import("./pages/ApplyLeavePage"));
const Balances=lazy(()=>import("./pages/BalancesPage"));
const Reviews=lazy(()=>import("./pages/ReviewsPage"));
const Admin=lazy(()=>import("./pages/AdminPage"));
export const routes:RouteObject[]=[{index:true,element:<Home/>},{path:"apply",element:<Apply/>},{path:"balances",element:<Balances/>},{path:"reviews",element:<Reviews/>},{path:"admin",element:<Admin/>},{path:"*",element:<Navigate to="." replace/>}];
