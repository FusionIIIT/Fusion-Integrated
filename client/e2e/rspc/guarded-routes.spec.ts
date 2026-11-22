import { expect, signedInAs, test } from "../support/test";

// Guarded RSPC routes: unauthorized roles attempting deep links must be blocked by NotPermitted.
const RSPC_GUARDED_PAGES = ["proposals", "projects", "finance"];

test.describe("rspc: guarded deep links", () => {
  test.use(signedInAs("student"));

  for (const path of RSPC_GUARDED_PAGES) {
    test(`a student who opens /rspc/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/rspc/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
