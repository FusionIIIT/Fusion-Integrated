// End-to-end Playwright workflows for PSM requester and procurement operations.
import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("psm: requester indent lifecycle", () => {
  test.use(signedInAs("psmRequester"));

  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext(signedInAs("psmRequester"));
    try {
      const meRes = await context.request.get("/api/v1/me");
      if (meRes.ok()) {
        const me = (await meRes.json()) as { active_role?: string; csrf_token?: string };
        if (me.active_role !== "faculty") {
          await context.request.patch("/api/v1/me", {
            headers: me.csrf_token ? { "X-CSRF-Token": me.csrf_token } : {},
            data: { active_role: "faculty" },
          });
        }
      }
    } finally {
      await context.close();
    }
  });

  test("faculty submits, views history, and withdraws an indent (PSM-UC-001, PSM-UC-005)", async ({ page }) => {
    const itemDesc = uniqueName("E2E Oscilloscope");

    await page.goto("/");
    await actAs(page, "psmRequester");
    await openModuleNav(page, "Procurement & Stores");
    await sidebar(page).getByRole("link", { name: "Indents" }).click();
    await expect(page.getByRole("heading", { name: "Purchase Indents", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "New indent" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Item description").fill(itemDesc);
    await dialog.getByLabel("Justification").fill("E2E lab bench verification");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/indents") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Submit indent" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: itemDesc });
    await expect(row).toBeVisible();

    const withdrawn = page.waitForResponse((r) =>
      r.url().includes("/withdraw") && r.request().method() === "POST");
    await row.getByRole("button", { name: "Withdraw" }).click();
    expect((await withdrawn).status()).toBe(200);
  });
});

test.describe("psm: procurement operations", () => {
  test.use(signedInAs("psAdmin"));

  test("ps_admin opens dashboard, onboards vendor, adds stock, and generates report (PSM-UC-019, 026, 010, 030)", async ({ page }) => {
    const vendorName = uniqueName("E2E Vendor");
    const sku = uniqueName("SKU").replace(/\s+/g, "-").slice(0, 24);

    await page.goto("/");
    await actAs(page, "psAdmin");
    await openModuleNav(page, "Procurement & Stores");
    await sidebar(page).getByRole("link", { name: "Dashboard", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Procurement & Stores Dashboard", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Vendors", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Vendors", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Onboard vendor" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Vendor name").fill(vendorName);
    await dialog.getByLabel("GSTIN").fill("23ABCDE1234F1Z5");
    await dialog.getByLabel("Bank account number").fill("123456789012");
    await dialog.getByLabel("Bank IFSC").fill("SBIN0001234");
    await dialog.getByLabel("Bank name").fill("SBI");
    await dialog.getByLabel("Compliance document reference").fill("gst.pdf");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/vendors") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save vendor" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    await expect(page.getByRole("row").filter({ hasText: vendorName })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
    await page.getByRole("button", { name: "Add stock item" }).click();
    const stockDialog = page.getByRole("dialog");
    await stockDialog.getByLabel("SKU").fill(sku);
    await stockDialog.getByLabel("Item name").fill("E2E Cable");
    const itemRes = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/stock/items") && r.request().method() === "POST");
    await stockDialog.getByRole("button", { name: "Create item" }).click();
    expect((await itemRes).status()).toBe(201);

    await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
    const repRes = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/reports/generate") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Generate report" }).click();
    expect((await repRes).status()).toBe(200);
  });
});
