import {lazy} from "react";
import {Navigate,type RouteObject} from "react-router-dom";
const IAAWorkspacePage=lazy(()=>import("./pages/IAAWorkspacePage").then(m=>({default:m.IAAWorkspacePage})));
export const routes:RouteObject[]=[
 {index:true,element:<Navigate to="requests" replace/>},
 {path:"requests",element:<IAAWorkspacePage section="requests"/>},
 {path:"ta",element:<IAAWorkspacePage section="ta"/>},
 {path:"finance",element:<IAAWorkspacePage section="finance"/>},
 {path:"approvals",element:<IAAWorkspacePage section="approvals"/>},
 {path:"anomalies",element:<IAAWorkspacePage section="anomalies"/>},
 {path:"observations",element:<IAAWorkspacePage section="observations"/>},
 {path:"reports",element:<IAAWorkspacePage section="reports"/>},
 {path:"notifications",element:<IAAWorkspacePage section="notifications"/>},
 {path:"configuration",element:<IAAWorkspacePage section="configuration"/>},
];
