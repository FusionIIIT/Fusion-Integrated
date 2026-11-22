import { expect, signedInAs, test } from "../support/test";

test.describe("vms: navigation and pages", () => {
  test.use(signedInAs("student"));

  test("user accesses visitor management passes and page elements", async ({ page }) => {
    await page.goto("/vms/passes");
    await expect(page.getByRole("heading", { name: "Visitor Passes", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /pre-register visitor/i })).toBeVisible();
  });

  test("user navigates to security gate scanner", async ({ page }) => {
    await page.goto("/vms/gate");
    await expect(page.getByRole("heading", { name: /security gate scanner/i, level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /validate pass/i })).toBeVisible();
  });

  test("user navigates to emergency evacuation muster", async ({ page }) => {
    await page.goto("/vms/emergency");
    await expect(page.getByRole("heading", { name: /emergency evacuation muster/i, level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /trigger evacuation muster/i })).toBeVisible();
  });

  test("user navigates to blacklist registry", async ({ page }) => {
    await page.goto("/vms/blacklist");
    await expect(page.getByRole("heading", { name: /blacklist & safe-list registry/i, level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /add to blacklist/i })).toBeVisible();
  });

  test("user views visitor analytics and audit log", async ({ page }) => {
    await page.goto("/vms/analytics");
    await expect(page.getByRole("heading", { name: /visitor analytics/i, level: 2 })).toBeVisible();
  });
});
