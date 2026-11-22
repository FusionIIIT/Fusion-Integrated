import { expect, signedInAs, test } from "../support/test";

// Office pages opened directly by an unauthorized role
const OFFICE_PAGES = [
  "reviews",
  "budget-approvals",
  "docket",
  "maintenance-decisions",
  "office-actions",
  "reports",
];

test.describe("patents: office pages", () => {
  test.use(signedInAs("student"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /patents/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/patents/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
