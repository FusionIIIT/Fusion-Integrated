import { expect, signedInAs, test } from "../support/test";

const PAGES = ["my-requests", "finance", "approvals", "anomalies", "observations", "reports",
  "notifications", "configuration"];
// What an ordinary employee must not reach, whatever the sidebar showed them.
const OFFICE_PAGES = ["finance", "approvals", "anomalies", "reports", "configuration"];

test.describe("iaa: a student, who has no access to the module", () => {
  test.use(signedInAs("student"));

  for (const path of PAGES) {
    test(`a student who opens /iaa/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/iaa/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});

test.describe("iaa: an ordinary employee, who may only raise requests", () => {
  test.use(signedInAs("iaaFaculty"));

  for (const path of OFFICE_PAGES) {
    test(`an employee who opens /iaa/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/iaa/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
