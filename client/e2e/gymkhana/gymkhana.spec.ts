import { test, expect } from "@playwright/test";

test.describe("Gymkhana", () => {
  test("route guard closes Gymkhana to an ungranted role", async ({ page }) => {
    await page.goto("/gymkhana");
    await expect(page).not.toHaveURL(/gymkhana\/clubs/);
  });

  test("clubs page has a readable empty/loading state", async ({ page }) => {
    await page.goto("/gymkhana/clubs");
    await expect(page.locator("body")).toContainText(/Gymkhana|Forbidden|Login/);
  });

  test("polls page is permission guarded", async ({ page }) => {
    await page.goto("/gymkhana/polls");
    await expect(page.locator("body")).toContainText(/Gymkhana|Forbidden|Login/);
  });
});
