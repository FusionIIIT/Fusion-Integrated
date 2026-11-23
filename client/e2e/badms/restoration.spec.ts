import { expect, signedInAs, test } from "../support/test";

test.describe("badms: data restorations", () => {
  test.use(signedInAs("student"));

  test("student views restorations page interface", async ({ page }) => {
    await page.goto("/badms/restorations");
    await expect(page.getByRole("heading", { name: "Data Restorations" })).toBeVisible();
    await expect(page.getByText("Manage point-in-time restoration requests and audit recovery operations")).toBeVisible();
  });
});
