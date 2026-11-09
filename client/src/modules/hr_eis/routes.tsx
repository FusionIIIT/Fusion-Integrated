
import { Navigate, type RouteObject } from "react-router-dom";

import EmployeeList from "./EmployeeList.jsx";
import DepartmentList from "./DepartmentList.jsx";
import PositionList from "./PositionList.jsx";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="employees" replace /> },
  { path: "employees", element: <EmployeeList /> },
  { path: "departments", element: <DepartmentList /> },
  { path: "positions", element: <PositionList /> },
];
