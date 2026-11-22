import { describe } from "vitest";

import PatientDashboardPage from "./PatientDashboardPage";
import { testPageStates } from "../testSupport";

describe("PatientDashboardPage", () => {
  testPageStates(PatientDashboardPage, "No published schedules are available.");
});
