import type { RouteObject } from "react-router-dom";
import LeaveApplicationForm from "./LeaveApplicationForm";

export const routes: RouteObject[] = [
  {
    index: true,
    element: <LeaveApplicationForm />,
  },
  {
    path: "apply",
    element: <LeaveApplicationForm />,
  },
];
