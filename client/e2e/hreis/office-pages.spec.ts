import { expect, signedInAs, test } from "../support/test";

// The office's pages, opened directly by someone the sidebar never offered them to.
const OFFICE_PAGES = [
  "approvals",
  "verification",
  "appraisal-admin",
  "admin",
  "audit",
  "settlement",
];

test.describe("hreis: office pages", () => {
  test.use(signedInAs("faculty"));

  for (const path of OFFICE_PAGES) {
    test(`a faculty who opens /hr/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/hr/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
