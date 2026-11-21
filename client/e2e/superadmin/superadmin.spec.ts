import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test,
} from "../support/test";

test.describe("superadmin: main flows", () => {
  test.use(signedInAs("superAdmin"));

  test("super admin views dashboard overview and metrics", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Dashboard" }).click();

    await expect(page.getByRole("heading", { name: "System Administration", level: 2 })).toBeVisible();
    await expect(page.getByText("Archived Users")).toBeVisible();
    await expect(page.getByText("Total Audit Events")).toBeVisible();
  });

  test("super admin navigates to policy governance and inspects parameters", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "System Policies" }).click();

    await expect(page.getByRole("heading", { name: "System Policies", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /supersede parameter/i })).toBeVisible();
  });

  test("super admin views audit compliance log", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Audit Logs" }).click();

    await expect(page.getByRole("heading", { name: "Audit Logs", level: 2 })).toBeVisible();
    await expect(page.getByPlaceholder(/search by actor username/i)).toBeVisible();
  });

  test("super admin views user archival records", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Archival Governance" }).click();

    await expect(page.getByRole("heading", { name: "Archival Governance", level: 2 })).toBeVisible();
  });
});

test.describe("superadmin: dual-auth purge flows", () => {
  test.use(signedInAs("itHead"));

  test("it head accesses purge authorization page", async ({ page }) => {
    await page.goto("/superadmin/purge");
    await actAs(page, "itHead");
    await expect(page.getByRole("heading", { name: "Purge Authorization", level: 2 })).toBeVisible();
  });
});
