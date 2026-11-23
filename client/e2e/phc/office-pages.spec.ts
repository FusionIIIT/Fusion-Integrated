import { actAs, expect, signedInAs, test } from "../support/test";

// Every guarded PHC route, opened directly by a role whose sidebar never offered it.
const NOT_FOR_STUDENTS = ["claims", "inventory", "requisitions", "ambulance", "reports"];
// Accounts & Audit holds only claim permissions.
const NOT_FOR_ACCOUNTS = ["schedule", "advisories", "records", "notifications"];

test.describe("phc: guarded pages, as a student", () => {
  test.use(signedInAs("student"));

  for (const path of NOT_FOR_STUDENTS) {
    test(`a student who opens /phc/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/phc/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});

test.describe("phc: guarded pages, as Accounts & Audit", () => {
  test.use(signedInAs("phcAccounts"));

  for (const path of NOT_FOR_ACCOUNTS) {
    test(`Accounts & Audit opening /phc/${path} is told it is not for them`, async ({ page }) => {
      await page.goto("/");
      await actAs(page, "phcAccounts");
      await page.goto(`/phc/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
