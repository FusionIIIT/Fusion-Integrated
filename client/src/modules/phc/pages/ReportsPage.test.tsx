import { describe } from "vitest";

import ReportsPage from "./ReportsPage";
import { testPageStates } from "../testSupport";

describe("ReportsPage", () => {
  testPageStates(ReportsPage, "No data is available for this report.");
});
