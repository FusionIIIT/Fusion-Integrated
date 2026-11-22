import { expect, signedInAs, test } from "../support/test";

test.describe("badms: database backups", () => {
  test.use(signedInAs("student"));

  test("student without manage permission is denied access to backups management", async ({ page }) => {
    await page.goto("/badms/backups");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("button", { name: /trigger manual backup/i })).toHaveCount(0);
  });
});
