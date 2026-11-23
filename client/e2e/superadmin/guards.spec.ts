import { expect, signedInAs, test } from "../support/test";

// Guarded superadmin routes that must refuse unpermitted roles on direct deep-link.
const SUPERADMIN_PAGES = ["dashboard", "archival", "purge", "policy", "audit"];

test.describe("superadmin: guarded route deep-links", () => {
  test.use(signedInAs("student"));

  for (const path of SUPERADMIN_PAGES) {
    test(`a student navigating to /superadmin/${path} is refused by route guard`, async ({ page }) => {
      await page.goto(`/superadmin/${path}`);
      await expect(page.getByText("module it belongs to is not enabled for your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
