import { expect, sidebar, signedInAs, test } from "./support/test";

test.describe("shell", () => {
  test.use(signedInAs("student"));

  test("the collapsed sidebar names each module for a screen reader", async ({ page }) => {
    await page.goto("/");
    const expand = sidebar(page).getByRole("button", { name: "Expand sidebar" });
    const collapse = sidebar(page).getByRole("button", { name: "Collapse sidebar" });
    await expect(expand.or(collapse)).toBeVisible();
    if (await collapse.isVisible()) await collapse.click();
    await expect(expand).toBeVisible();

    await expect(sidebar(page).getByRole("button", { name: "Placement Cell" })).toBeVisible();
  });
});
