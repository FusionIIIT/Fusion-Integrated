import { describe } from "vitest";

import NotificationsPage from "./NotificationsPage";
import { testPageStates } from "../testSupport";

describe("NotificationsPage", () => {
  testPageStates(NotificationsPage, "You have no PHC notifications.");
});
