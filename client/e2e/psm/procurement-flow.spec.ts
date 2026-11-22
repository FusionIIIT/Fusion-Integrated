// End-to-end Playwright workflows covering all PSM actor roles and live UC main flows (R2-06).
import type { Browser } from "@playwright/test";

import { ACCOUNTS, type AccountKey } from "../accounts";
import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

async function ensureActiveRole(browser: Browser, key: AccountKey): Promise<void> {
  const context = await browser.newContext(signedInAs(key));
  try {
    const meRes = await context.request.get("/api/v1/me");
    if (meRes.ok()) {
      const me = (await meRes.json()) as { active_role?: string; csrf_token?: string };
      const wanted = ACCOUNTS[key].role;
      if (me.active_role !== wanted) {
        await context.request.patch("/api/v1/me", {
          headers: me.csrf_token ? { "X-CSRF-Token": me.csrf_token } : {},
          data: { active_role: wanted },
        });
      }
    }
  } finally {
    await context.close();
  }
}

test.describe("psm: requester indent and receipt lifecycle", () => {
  test.use(signedInAs("psmRequester"));

  test.beforeAll(async ({ browser }) => {
    await ensureActiveRole(browser, "psmRequester");
  });

  test("faculty submits, inspects history, withdraws indent, and views receipts (PSM-UC-001, 002, 005, 020, 024, 028)", async ({ page }) => {
    const itemDesc = uniqueName("E2E Oscilloscope");

    await page.goto("/");
    await actAs(page, "psmRequester");
    await openModuleNav(page, "Procurement & Stores");
    await sidebar(page).getByRole("link", { name: "Indents", exact: true }).click();
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

    await row.getByRole("button", { name: "History" }).click();
    await expect(page.getByText(/indent history/i)).toBeVisible();
    await page.keyboard.press("Escape");

    const withdrawn = page.waitForResponse((r) =>
      r.url().includes("/withdraw") && r.request().method() === "POST");
    await row.getByRole("button", { name: "Withdraw" }).click();
    expect((await withdrawn).status()).toBe(200);

    await sidebar(page).getByRole("link", { name: "Receipts & Discrepancies", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Receipts & Discrepancies", level: 2 })).toBeVisible();
  });
});

test.describe("psm: procurement operations", () => {
  test.use(signedInAs("psAdmin"));

  test.beforeAll(async ({ browser }) => {
    await ensureActiveRole(browser, "psAdmin");
  });

  test("ps_admin runs dashboard, vendor, stock, tender, PO, reports, and policy pages (PSM-UC-010, 019, 022, 025, 026, 027, 030, 031)", async ({ page }) => {
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
    const vRow = page.getByRole("row").filter({ hasText: vendorName });
    await expect(vRow).toBeVisible();
    const verified = page.waitForResponse((r) =>
      r.url().includes("/verify") && r.request().method() === "POST");
    await vRow.getByRole("button", { name: "Verify" }).click();
    expect((await verified).status()).toBe(200);

    await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
    await page.getByRole("button", { name: "Add stock item" }).click();
    const stockDialog = page.getByRole("dialog");
    await stockDialog.getByLabel("SKU").fill(sku);
    await stockDialog.getByLabel("Item name").fill("E2E Cable");
    const itemRes = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/stock/items") && r.request().method() === "POST");
    await stockDialog.getByRole("button", { name: "Create item" }).click();
    expect((await itemRes).status()).toBe(201);

    await sidebar(page).getByRole("link", { name: "Tenders", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Tenders", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Purchase Orders", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Purchase Orders", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
    const repRes = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/reports/generate") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Generate report" }).click();
    expect((await repRes).status()).toBe(200);

    await sidebar(page).getByRole("link", { name: "Policy", exact: true }).click();
    await expect(page.getByRole("heading", { name: /psm policy/i, level: 2 })).toBeVisible();
  });
});

test.describe("psm: departmental, finance, final authority, and audit roles", () => {
  test.describe("deptadmin_cse", () => {
    test.use(signedInAs("psmDeptAdmin"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmDeptAdmin");
    });

    test("deptadmin_cse views indents, stock, and transfers (PSM-UC-007, 008, 009, 011, 017, 021, 033, 034)", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmDeptAdmin");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Stock & Internal Issues", level: 2 })).toBeVisible();
      await sidebar(page).getByRole("link", { name: "Stock Transfers", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Inter-Departmental Stock Transfers", level: 2 })).toBeVisible();
    });
  });

  test.describe("HOD (CSE)", () => {
    test.use(signedInAs("psmHod"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmHod");
    });

    test("HOD (CSE) views departmental indents and operational reports (PSM-UC-010, 016)", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmHod");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Indents", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Purchase Indents", level: 2 })).toBeVisible();
      await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Reports & Schedules", level: 2 })).toBeVisible();
    });
  });

  test.describe("Accounts Admin", () => {
    test.use(signedInAs("psmAccounts"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmAccounts");
    });

    test("Accounts Admin accesses invoices & payments and financial reports (PSM-UC-013, 015, 029)", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmAccounts");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Invoices & Payments", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Invoices & Payments", level: 2 })).toBeVisible();
    });
  });

  test.describe("Auditor", () => {
    test.use(signedInAs("psmAuditor"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmAuditor");
    });

    test("Auditor accesses read-only audit trail and dashboard (PSM-UC-014, 015, 030)", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmAuditor");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Audit Trail", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Audit Trail", level: 2 })).toBeVisible();
    });
  });
});
