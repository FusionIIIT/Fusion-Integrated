import { expect, signedInAs, test } from "../support/test";

const OFFICE_PAGES = ["verification", "decisions", "awards"];

test.describe("spacs: office pages", () => {
  test.use(signedInAs("student"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /spacs/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/spacs/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
