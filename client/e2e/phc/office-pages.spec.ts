import { expect, signedInAs, test } from "../support/test";

const RESTRICTED_ROUTES = [
  "staff/visits",
  "staff/schedules",
  "staff/attendance",
  "staff/inventory",
  "staff/requisitions",
  "staff/ambulance",
  "staff/advisories",
  "staff/reports",
  "accounts/claims",
  "authority/claims",
  "authority/requisitions",
  "notifications",
];

test.describe("phc: direct links respect role permissions", () => {
  test.use(signedInAs("student"));

  for (const route of RESTRICTED_ROUTES) {
    test(`student direct link to /phc/${route} is refused`, async ({ page }) => {
      await page.goto(`/phc/${route}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
