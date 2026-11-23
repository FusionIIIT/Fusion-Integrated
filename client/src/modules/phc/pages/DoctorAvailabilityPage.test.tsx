import { describe } from "vitest";

import DoctorAvailabilityPage from "./DoctorAvailabilityPage";
import { testPageStates } from "../testSupport";

describe("DoctorAvailabilityPage", () => {
  testPageStates(DoctorAvailabilityPage, "No published doctor schedules are available.");
});
