// Verify every guarded PSM office route refuses a user without the required grant.
import { expect, signedInAs, test } from "../support/test";

const GUARDED_PSM_PAGES = [
  "stock",
  "transfers",
  "vendors",
  "tenders",
  "purchase-orders",
  "invoices",
  "reports",
  "audit",
  "policy",
];

test.describe("psm: guarded pages", () => {
  test.use(signedInAs("student"));

  for (const path of GUARDED_PSM_PAGES) {
    test(`a student who opens /psm/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/psm/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
