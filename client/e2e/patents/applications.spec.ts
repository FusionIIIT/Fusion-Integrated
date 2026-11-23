import { expect, signedInAs, test } from "../support/test";

test.describe("patents: applicant pages", () => {
  test.use(signedInAs("student"));

  test("an applicant can navigate to my applications page", async ({ page }) => {
    await page.goto("/patents");
    await expect(page).toHaveURL(/\/patents/);
  });

  test("an applicant can open the new application submission page", async ({ page }) => {
    await page.goto("/patents/new");
    await expect(page).toHaveURL(/\/patents\/new/);
  });
});
