import { expect, signedInAs, test } from "../support/test";

// PHC office pages, opened directly by a student the sidebar never offered them to.
const OFFICE_PAGES = ["inventory", "requisitions", "ambulance", "reports"];

test.describe("phc: office pages", () => {
  test.use(signedInAs("student"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /phc/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/phc/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
