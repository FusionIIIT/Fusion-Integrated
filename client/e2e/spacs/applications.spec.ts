import { expect, signedInAs, test } from "../support/test";

test.describe("spacs: student applications", () => {
  test.use(signedInAs("student"));

  test("a student views available scholarship opportunities", async ({ page }) => {
    await page.goto("/spacs/catalogue");
    await expect(page.getByRole("heading", { name: "Scholarship and Award Opportunities" })).toBeVisible();
  });

  test("a student views my applications page", async ({ page }) => {
    await page.goto("/spacs/mine");
    await expect(page.getByRole("heading", { name: "My Applications" })).toBeVisible();
  });
});
