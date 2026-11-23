// End-to-end Playwright workflows covering all 31 actor-triggered PSM UCs plus event-triggered PSM-UC-035 (R3-03).
import type { Browser, Page } from "@playwright/test";

import { ACCOUNTS, type AccountKey } from "../accounts";
import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

interface SharedPsmState {
  stockItemId: number;
  sku: string;
  centralLocationId: number;
  cseLocationId: number;
  cseSecondaryLocationId: number;
  internalIndentDesc: string;
  internalIssueId: number;
  directIndentId: number;
  directIndentDesc: string;
  tenderIndentId: number;
  tenderIndentDesc: string;
  vendorId: number;
  vendorName: string;
  directPoId: number;
  directPoNumber: string;
  grnId: number;
  grnNumber: string;
}

const state: SharedPsmState = {
  stockItemId: 0,
  sku: "",
  centralLocationId: 0,
  cseLocationId: 0,
  cseSecondaryLocationId: 0,
  internalIndentDesc: "",
  internalIssueId: 0,
  directIndentId: 0,
  directIndentDesc: "",
  tenderIndentId: 0,
  tenderIndentDesc: "",
  vendorId: 0,
  vendorName: "",
  directPoId: 0,
  directPoNumber: "",
  grnId: 0,
  grnNumber: "",
};

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

async function apiPost(page: Page, path: string, data: Record<string, unknown>) {
  const meRes = await page.request.get("/api/v1/me");
  const me = (await meRes.json()) as { csrf_token?: string };
  const res = await page.request.post(path, {
    headers: me.csrf_token ? { "X-CSRF-Token": me.csrf_token } : {},
    data,
  });
  expect(res.ok(), `POST ${path} failed: ${res.status()}`).toBeTruthy();
  return res.json();
}

test.describe.serial("psm: full multi-role procurement and stores lifecycle", () => {
  test.describe("1. ps_admin setup: vendor onboarding, stock item, locations, and central stock adjustment (PSM-UC-008, 019, 030)", () => {
    test.use(signedInAs("psAdmin"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psAdmin");
    });

    test("ps_admin views dashboard, onboards and verifies vendor, creates stock item and locations, and posts adjustment", async ({
      page,
    }) => {
      state.vendorName = uniqueName("E2E Vendor");
      state.sku = uniqueName("SKU").replace(/\s+/g, "-").slice(0, 24);
      const centralCode = uniqueName("CEN").replace(/\s+/g, "-").slice(0, 18).toUpperCase();
      const cseCode = uniqueName("CSE").replace(/\s+/g, "-").slice(0, 18).toUpperCase();
      const cse2Code = uniqueName("CS2").replace(/\s+/g, "-").slice(0, 18).toUpperCase();

      await page.goto("/");
      await actAs(page, "psAdmin");
      await openModuleNav(page, "Procurement & Stores");

      // PSM-UC-030: View Procurement & Stock Dashboard.
      await sidebar(page).getByRole("link", { name: "Dashboard", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Procurement & Stores Dashboard", level: 2 })).toBeVisible();

      // PSM-UC-019: Onboard and Maintain Vendor Master Data.
      await sidebar(page).getByRole("link", { name: "Vendors", exact: true }).click();
      await page.getByRole("button", { name: "Onboard vendor" }).click();
      const vDialog = page.getByRole("dialog");
      await vDialog.getByLabel("Vendor name").fill(state.vendorName);
      await vDialog.getByLabel("GSTIN").fill("23ABCDE1234F1Z5");
      await vDialog.getByLabel("Bank account number").fill("123456789012");
      await vDialog.getByLabel("Bank IFSC").fill("SBIN0001234");
      await vDialog.getByLabel("Bank name").fill("SBI");
      await vDialog.getByLabel("Compliance document reference").fill("gst.pdf");

      const vCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/vendors") && r.request().method() === "POST",
      );
      await vDialog.getByRole("button", { name: "Save vendor" }).click();
      const vRes = await vCreated;
      expect(vRes.status()).toBe(201);
      state.vendorId = ((await vRes.json()) as { id: number }).id;

      await expect(vDialog).toBeHidden();
      const vRow = page.getByRole("row").filter({ hasText: state.vendorName });
      await expect(vRow).toBeVisible();
      const vVerified = page.waitForResponse(
        (r) => r.url().includes("/verify") && r.request().method() === "POST",
      );
      await vRow.getByRole("button", { name: "Verify" }).click();
      expect((await vVerified).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.vendorName })).toContainText("Verified");

      // Create stock item via UI modal on /psm/stock.
      await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
      await page.getByRole("button", { name: "Add stock item" }).click();
      const itemDialog = page.getByRole("dialog");
      await itemDialog.getByLabel("SKU").fill(state.sku);
      await itemDialog.getByLabel("Item name").fill("E2E Network Switch");
      const itemCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/stock/items") && r.request().method() === "POST",
      );
      await itemDialog.getByRole("button", { name: "Create item" }).click();
      const itemRes = await itemCreated;
      expect(itemRes.status()).toBe(201);
      state.stockItemId = ((await itemRes.json()) as { id: number }).id;
      await expect(itemDialog).toBeHidden();

      // Create central and CSE locations via authenticated session so stock adjustment & transfer UI modals can target them.
      const centralLoc = (await apiPost(page, "/api/v1/psm/stock/locations", {
        code: centralCode,
        name: "Central Store E2E",
        department: "CENTRAL",
        is_central: true,
      })) as { id: number };
      state.centralLocationId = centralLoc.id;
      const cseLoc = (await apiPost(page, "/api/v1/psm/stock/locations", {
        code: cseCode,
        name: "CSE Dept Store E2E",
        department: "CSE",
        is_central: false,
      })) as { id: number };
      state.cseLocationId = cseLoc.id;
      const cse2Loc = (await apiPost(page, "/api/v1/psm/stock/locations", {
        code: cse2Code,
        name: "CSE Annex Store E2E",
        department: "CSE",
        is_central: false,
      })) as { id: number };
      state.cseSecondaryLocationId = cse2Loc.id;

      // PSM-UC-008: Record Stock Adjustment via UI modal on /psm/stock.
      await page.getByRole("button", { name: "Record adjustment" }).click();
      const adjDialog = page.getByRole("dialog");
      await adjDialog.getByLabel("Item ID").fill(String(state.stockItemId));
      await adjDialog.getByLabel("Location ID").fill(String(state.centralLocationId));
      await adjDialog.getByLabel("Quantity delta").fill("40");
      await adjDialog.getByLabel("Adjustment reason").fill("Opening central stock for E2E");
      const adjPosted = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/stock/adjustments") && r.request().method() === "POST",
      );
      await adjDialog.getByRole("button", { name: "Post adjustment" }).click();
      expect((await adjPosted).status()).toBe(201);
      await expect(adjDialog).toBeHidden();
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.sku }).first()).toBeVisible();
    });
  });

  test.describe("2. faculty requester indent lifecycle (PSM-UC-001, 003, 005, 023, 024)", () => {
    test.use(signedInAs("psmRequester"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmRequester");
    });

    test("faculty submits indents, views history, modifies, repeats, and withdraws via UI", async ({
      page,
    }) => {
      const withdrawDesc = uniqueName("E2E Withdraw Indent");
      state.internalIndentDesc = uniqueName("E2E Internal Stock Indent");
      state.directIndentDesc = uniqueName("E2E Direct PO Indent");
      state.tenderIndentDesc = uniqueName("E2E High Value Tender Indent");

      await page.goto("/");
      await actAs(page, "psmRequester");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Indents", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Purchase Indents", level: 2 })).toBeVisible();

      // PSM-UC-001: Submit Purchase Indent (for modify/repeat/withdraw).
      await page.getByRole("button", { name: "New indent" }).click();
      const dialog1 = page.getByRole("dialog");
      await dialog1.getByLabel("Item description").fill(withdrawDesc);
      await dialog1.getByLabel("Quantity").fill("2");
      await dialog1.getByLabel("Estimated cost").fill("4000.00");
      await dialog1.getByLabel("Justification").fill("E2E modify repeat withdraw test");
      const created1 = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents") && r.request().method() === "POST",
      );
      await dialog1.getByRole("button", { name: "Submit indent" }).click();
      expect((await created1).status()).toBe(201);
      await expect(dialog1).toBeHidden();

      const row1 = page.getByRole("row").filter({ hasText: withdrawDesc }).first();
      await expect(row1).toBeVisible();

      // PSM-UC-003: Track Indent Status & History.
      await row1.getByRole("button", { name: "History" }).click();
      await expect(page.getByText(/indent history/i)).toBeVisible();
      await page.keyboard.press("Escape");

      // PSM-UC-023: Modify Pending Indent via UI button.
      const modified = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents/") && r.request().method() === "PATCH",
      );
      await row1.getByRole("button", { name: "Modify" }).click();
      expect((await modified).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: withdrawDesc }).first()).toContainText("v2");

      // PSM-UC-024: Repeat Previous Indent as Draft, edit draft in place (RQ1-01), then submit draft.
      const repeated = page.waitForResponse(
        (r) => r.url().includes("/repeat") && r.request().method() === "POST",
      );
      await page.getByRole("row").filter({ hasText: withdrawDesc }).first().getByRole("button", { name: "Repeat" }).click();
      expect((await repeated).status()).toBe(201);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: withdrawDesc })).toHaveCount(2);

      const draftRow = page.getByRole("row").filter({ hasText: withdrawDesc }).filter({ hasText: "draft" });
      const draftModified = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents/") && r.request().method() === "PATCH",
      );
      await draftRow.getByRole("button", { name: "Modify" }).click();
      expect((await draftModified).status()).toBe(200);
      await page.reload();
      await expect(
        page.getByRole("row").filter({ hasText: withdrawDesc }).filter({ hasText: "draft" }),
      ).toContainText("v2");

      const draftSubmitted = page.waitForResponse(
        (r) => r.url().includes("/submit") && r.request().method() === "POST",
      );
      await page
        .getByRole("row")
        .filter({ hasText: withdrawDesc })
        .filter({ hasText: "draft" })
        .getByRole("button", { name: "Submit draft" })
        .click();
      expect((await draftSubmitted).status()).toBe(200);
      await page.reload();
      await expect(
        page.getByRole("row").filter({ hasText: withdrawDesc }).filter({ hasText: "submitted" }),
      ).toHaveCount(2);

      // PSM-UC-005: Withdraw or Cancel Pending Indent via UI button.
      const submittedRow = page
        .getByRole("row")
        .filter({ hasText: withdrawDesc })
        .filter({ hasText: "submitted" })
        .first();
      const withdrawn = page.waitForResponse(
        (r) => r.url().includes("/withdraw") && r.request().method() === "POST",
      );
      await submittedRow.getByRole("button", { name: "Withdraw" }).click();
      expect((await withdrawn).status()).toBe(200);
      await page.reload();
      await expect(
        page.getByRole("row").filter({ hasText: withdrawDesc }).filter({ hasText: "withdrawn" }),
      ).toBeVisible();

      // Submit Indent #2: linked to stockItemId for Internal Stock Fulfilment (BW-PSM-01).
      await page.getByRole("button", { name: "New indent" }).click();
      const dialog2 = page.getByRole("dialog");
      await dialog2.getByLabel("Item description").fill(state.internalIndentDesc);
      await dialog2.getByLabel("Stock item ID (optional)").fill(String(state.stockItemId));
      await dialog2.getByLabel("Quantity").fill("3");
      await dialog2.getByLabel("Estimated cost").fill("6000.00");
      await dialog2.getByLabel("Justification").fill("Internal stock fulfilment flow");
      const created2 = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents") && r.request().method() === "POST",
      );
      await dialog2.getByRole("button", { name: "Submit indent" }).click();
      expect((await created2).status()).toBe(201);
      await expect(dialog2).toBeHidden();

      // Submit Indent #3: External Direct Procurement (<= 50000, no stock item).
      await page.getByRole("button", { name: "New indent" }).click();
      const dialog3 = page.getByRole("dialog");
      await dialog3.getByLabel("Item description").fill(state.directIndentDesc);
      await dialog3.getByLabel("Quantity").fill("4");
      await dialog3.getByLabel("Estimated cost").fill("20000.00");
      await dialog3.getByLabel("Justification").fill("External direct procurement flow");
      const created3 = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents") && r.request().method() === "POST",
      );
      await dialog3.getByRole("button", { name: "Submit indent" }).click();
      const res3 = await created3;
      expect(res3.status()).toBe(201);
      state.directIndentId = ((await res3.json()) as { id: number }).id;
      await expect(dialog3).toBeHidden();

      // Submit Indent #4: External High-Value Tender Procurement (> 100000).
      await page.getByRole("button", { name: "New indent" }).click();
      const dialog4 = page.getByRole("dialog");
      await dialog4.getByLabel("Item description").fill(state.tenderIndentDesc);
      await dialog4.getByLabel("Quantity").fill("2");
      await dialog4.getByLabel("Estimated cost").fill("150000.00");
      await dialog4.getByLabel("Justification").fill("High value tender flow");
      const created4 = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/indents") && r.request().method() === "POST",
      );
      await dialog4.getByRole("button", { name: "Submit indent" }).click();
      const res4 = await created4;
      expect(res4.status()).toBe(201);
      state.tenderIndentId = ((await res4.json()) as { id: number }).id;
      await expect(dialog4).toBeHidden();
    });
  });

  test.describe("3. deptadmin_cse stock, transfer, and indent review operations (PSM-UC-007, 008, 009, 011, 017, 021, 033, 034)", () => {
    test.use(signedInAs("psmDeptAdmin"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmDeptAdmin");
    });

    test("deptadmin_cse views and adjusts CSE stock, checks stock, approves indent review, dispatches internal issue, and completes stock transfer", async ({
      page,
    }) => {
      await page.goto("/");
      await actAs(page, "psmDeptAdmin");
      await openModuleNav(page, "Procurement & Stores");

      // PSM-UC-017: View Departmental Stock Availability & PSM-UC-008: Record Stock Adjustment on CSE store.
      await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Stock & Internal Issues", level: 2 })).toBeVisible();
      await page.getByRole("button", { name: "Record adjustment" }).click();
      const adjDialog = page.getByRole("dialog");
      await adjDialog.getByLabel("Item ID").fill(String(state.stockItemId));
      await adjDialog.getByLabel("Location ID").fill(String(state.cseLocationId));
      await adjDialog.getByLabel("Quantity delta").fill("15");
      await adjDialog.getByLabel("Adjustment reason").fill("Opening CSE departmental stock");
      const adjRes = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/stock/adjustments") && r.request().method() === "POST",
      );
      await adjDialog.getByRole("button", { name: "Post adjustment" }).click();
      expect((await adjRes).status()).toBe(201);
      await expect(adjDialog).toBeHidden();
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.sku }).first()).toBeVisible();

      // PSM-UC-007 (Check Stock & Reserve) & PSM-UC-011 (Dept Admin Review & Decision) on internal, direct, and tender indents.
      await sidebar(page).getByRole("link", { name: "Indents", exact: true }).click();
      for (const desc of [state.internalIndentDesc, state.directIndentDesc, state.tenderIndentDesc]) {
        const row = page.getByRole("row").filter({ hasText: desc });
        const scRes = page.waitForResponse(
          (r) => r.url().includes("/stock-check") && r.request().method() === "POST",
        );
        await row.getByRole("button", { name: "Check stock" }).click();
        expect((await scRes).status()).toBe(200);

        const revRes = page.waitForResponse(
          (r) => r.url().includes("/review") && r.request().method() === "POST",
        );
        await row.getByRole("button", { name: "Approve review" }).click();
        expect((await revRes).status()).toBe(200);
      }
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.internalIndentDesc })).toContainText(
        "internal_approved",
      );
      await expect(page.getByRole("row").filter({ hasText: state.directIndentDesc })).toContainText(
        "department_reviewed",
      );
      await expect(page.getByRole("row").filter({ hasText: state.tenderIndentDesc })).toContainText(
        "department_reviewed",
      );

      // PSM-UC-009: Dispatch Internal Stock Issue on /psm/stock.
      await sidebar(page).getByRole("link", { name: "Stock & Issues", exact: true }).click();
      const issueRow = page.getByRole("row").filter({ hasText: state.internalIndentDesc });
      await expect(issueRow).toBeVisible();
      const dispIssue = page.waitForResponse(
        (r) => r.url().includes("/internal-issues/") && r.url().includes("/dispatch"),
      );
      await issueRow.getByRole("button", { name: "Dispatch" }).click();
      const dispIssueRes = await dispIssue;
      expect(dispIssueRes.status()).toBe(200);
      state.internalIssueId = ((await dispIssueRes.json()) as { id: number }).id;
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.internalIndentDesc })).toContainText(
        "dispatched",
      );

      // PSM-UC-021 (Request Transfer), PSM-UC-033 (Dispatch Transfer), PSM-UC-034 (Confirm Transfer Receipt) on /psm/transfers.
      await sidebar(page).getByRole("link", { name: "Stock Transfers", exact: true }).click();
      await expect(
        page.getByRole("heading", { name: "Inter-Departmental Stock Transfers", level: 2 }),
      ).toBeVisible();
      await page.getByRole("button", { name: "Request transfer" }).click();
      const trfDialog = page.getByRole("dialog");
      await trfDialog.getByLabel("Item ID").fill(String(state.stockItemId));
      await trfDialog.getByLabel("Source location ID").fill(String(state.cseLocationId));
      await trfDialog.getByLabel("Destination location ID").fill(String(state.cseSecondaryLocationId));
      await trfDialog.getByLabel("Quantity").fill("2");
      await trfDialog.getByLabel("Notes").fill("E2E CSE main to CSE annex transfer");
      const trfCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/transfers") && r.request().method() === "POST",
      );
      await trfDialog.getByRole("button", { name: "Submit request" }).click();
      const trfRes = await trfCreated;
      expect(trfRes.status()).toBe(201);
      const trfNum = ((await trfRes.json()) as { transfer_number: string }).transfer_number;
      await expect(trfDialog).toBeHidden();

      const trfRow = page.getByRole("row").filter({ hasText: trfNum });
      const trfDisp = page.waitForResponse(
        (r) => r.url().includes("/transfers/") && r.url().includes("/dispatch"),
      );
      await trfRow.getByRole("button", { name: "Dispatch" }).click();
      expect((await trfDisp).status()).toBe(200);

      const trfConf = page.waitForResponse(
        (r) => r.url().includes("/transfers/") && r.url().includes("/confirm"),
      );
      await trfRow.getByRole("button", { name: "Confirm receipt" }).click();
      expect((await trfConf).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: trfNum })).toContainText("completed");
    });
  });

  test.describe("4. HOD (CSE) recommendation and operational report generation (PSM-UC-010, 016)", () => {
    test.use(signedInAs("psmHod"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmHod");
    });

    test("HOD (CSE) recommends department-reviewed indents and generates an operational report", async ({
      page,
    }) => {
      await page.goto("/");
      await actAs(page, "psmHod");
      await openModuleNav(page, "Procurement & Stores");

      // PSM-UC-016: Department Head Review & Recommendation.
      await sidebar(page).getByRole("link", { name: "Indents", exact: true }).click();
      for (const desc of [state.directIndentDesc, state.tenderIndentDesc]) {
        const row = page.getByRole("row").filter({ hasText: desc });
        const recRes = page.waitForResponse(
          (r) => r.url().includes("/recommend") && r.request().method() === "POST",
        );
        await row.getByRole("button", { name: "Recommend" }).click();
        expect((await recRes).status()).toBe(200);
      }
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.directIndentDesc })).toContainText(
        "hod_recommended",
      );
      await expect(page.getByRole("row").filter({ hasText: state.tenderIndentDesc })).toContainText(
        "hod_recommended",
      );

      // PSM-UC-010: Generate Operational, Procurement, and Stock Reports.
      await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
      const repRes = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/reports/generate") && r.request().method() === "POST",
      );
      await page.getByRole("button", { name: "Generate report" }).click();
      expect((await repRes).status()).toBe(200);
      await expect(page.getByText(/generated operational report/i)).toBeVisible();
    });
  });

  test.describe("5. ps_admin method selection (PSM-UC-025) and Director final approval (PSM-UC-012)", () => {
    test("ps_admin selects procurement method and Director grants final approval on high-value indent", async ({
      browser,
    }) => {
      await ensureActiveRole(browser, "psAdmin");
      const psCtx = await browser.newContext(signedInAs("psAdmin"));
      const psPage = await psCtx.newPage();
      try {
        await psPage.goto("/");
        await actAs(psPage, "psAdmin");
        await openModuleNav(psPage, "Procurement & Stores");
        await sidebar(psPage).getByRole("link", { name: "Indents", exact: true }).click();

        // PSM-UC-025: Procurement Review & Method Selection for direct and tender indents.
        for (const desc of [state.directIndentDesc, state.tenderIndentDesc]) {
          const row = psPage.getByRole("row").filter({ hasText: desc });
          const revRes = psPage.waitForResponse(
            (r) => r.url().includes("/procurement-review") && r.request().method() === "POST",
          );
          await row.getByRole("button", { name: "Select method" }).click();
          expect((await revRes).status()).toBe(200);
        }
        await psPage.reload();
        await expect(
          psPage.getByRole("row").filter({ hasText: state.directIndentDesc }),
        ).toContainText("procurement_authorized");
        await expect(
          psPage.getByRole("row").filter({ hasText: state.tenderIndentDesc }),
        ).toContainText("awaiting_final_approval");
      } finally {
        await psCtx.close();
      }

      // PSM-UC-012: Director / Registrar Final Approval for High-Value Procurement.
      await ensureActiveRole(browser, "psmDirector");
      const dirCtx = await browser.newContext(signedInAs("psmDirector"));
      const dirPage = await dirCtx.newPage();
      try {
        await dirPage.goto("/");
        await actAs(dirPage, "psmDirector");
        await openModuleNav(dirPage, "Procurement & Stores");
        await sidebar(dirPage).getByRole("link", { name: "Indents", exact: true }).click();
        const row = dirPage.getByRole("row").filter({ hasText: state.tenderIndentDesc });
        const finRes = dirPage.waitForResponse(
          (r) => r.url().includes("/final-decision") && r.request().method() === "POST",
        );
        await row.getByRole("button", { name: "Final approve" }).click();
        expect((await finRes).status()).toBe(200);
        await dirPage.reload();
        await expect(
          dirPage.getByRole("row").filter({ hasText: state.tenderIndentDesc }),
        ).toContainText("procurement_authorized");
      } finally {
        await dirCtx.close();
      }
    });
  });

  test.describe("6. ps_admin tender publication, PO issuance, delivery tracking, scheduled reports, and policy (PSM-UC-022, 026, 027, 031)", () => {
    test.use(signedInAs("psAdmin"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psAdmin");
    });

    test("ps_admin creates and publishes tender, issues and updates PO, schedules report, and publishes policy", async ({
      page,
    }) => {
      const tenderTitle = uniqueName("E2E Server Tender");
      const scheduleName = uniqueName("E2E Weekly Stock Schedule");

      await page.goto("/");
      await actAs(page, "psAdmin");
      await openModuleNav(page, "Procurement & Stores");

      // PSM-UC-022: Create and Publish Tender on /psm/tenders.
      await sidebar(page).getByRole("link", { name: "Tenders", exact: true }).click();
      await page.getByRole("button", { name: "New tender" }).click();
      const tDialog = page.getByRole("dialog");
      await tDialog.getByLabel("Indent ID").fill(String(state.tenderIndentId));
      await tDialog.getByLabel("Tender title").fill(tenderTitle);
      await tDialog.getByLabel("Scope").fill("Supply and installation of rack servers");
      await tDialog.getByLabel("Evaluation criteria").fill("Technical 70%, Financial 30%");
      const tCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/tenders") && r.request().method() === "POST",
      );
      await tDialog.getByRole("button", { name: "Create tender" }).click();
      expect((await tCreated).status()).toBe(201);
      await expect(tDialog).toBeHidden();

      const tRow = page.getByRole("row").filter({ hasText: tenderTitle });
      const tPub = page.waitForResponse(
        (r) => r.url().includes("/publish") && r.request().method() === "POST",
      );
      await tRow.getByRole("button", { name: "Publish" }).click();
      expect((await tPub).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: tenderTitle })).toContainText("published");

      // PSM-UC-026 (Create and Issue PO) & PSM-UC-027 (Track PO Status & Delivery Schedule) on /psm/purchase-orders.
      await sidebar(page).getByRole("link", { name: "Purchase Orders", exact: true }).click();
      await page.getByRole("button", { name: "Issue PO" }).click();
      const poDialog = page.getByRole("dialog");
      await poDialog.getByLabel("Indent ID").fill(String(state.directIndentId));
      await poDialog.getByLabel("Vendor ID").fill(String(state.vendorId));
      await poDialog.getByLabel("Unit price").fill("5000.00");
      const poCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/purchase-orders") && r.request().method() === "POST",
      );
      await poDialog.getByRole("button", { name: "Issue PO" }).click();
      const poRes = await poCreated;
      expect(poRes.status()).toBe(201);
      const poBody = (await poRes.json()) as { id: number; po_number: string };
      state.directPoId = poBody.id;
      state.directPoNumber = poBody.po_number;
      await expect(poDialog).toBeHidden();

      const poRow = page.getByRole("row").filter({ hasText: state.directPoNumber });
      const poUpd = page.waitForResponse(
        (r) => r.url().includes(`/api/v1/psm/purchase-orders/${state.directPoId}`) && r.request().method() === "PATCH",
      );
      await poRow.getByRole("button", { name: "Mark in transit" }).click();
      expect((await poUpd).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: state.directPoNumber })).toContainText(
        "in_transit",
      );

      // PSM-UC-031 & PSM-UC-035: Configure and Execute Scheduled Report on /psm/reports.
      await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
      await page.getByRole("button", { name: "Schedule report" }).click();
      const sDialog = page.getByRole("dialog");
      await sDialog.getByLabel("Schedule name").fill(scheduleName);
      const sCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/reports/schedules") && r.request().method() === "POST",
      );
      await sDialog.getByRole("button", { name: "Save schedule" }).click();
      expect((await sCreated).status()).toBe(201);
      await expect(sDialog).toBeHidden();
      await page.reload();
      const schedRow = page.getByRole("row").filter({ hasText: scheduleName });
      await expect(schedRow).toContainText("Active");

      const schedRun = page.waitForResponse(
        (r) => r.url().includes("/reports/schedules/") && r.url().includes("/run") && r.request().method() === "POST",
      );
      await schedRow.getByRole("button", { name: "Run now" }).click();
      expect((await schedRun).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("heading", { name: "Report Generation Logs" })).toBeVisible();
      const logRow = page.getByRole("row").filter({ hasText: scheduleName }).filter({ hasText: "scheduled" });
      await expect(logRow).toContainText("succeeded");
      await expect(page.getByRole("row").filter({ hasText: scheduleName }).filter({ hasText: "Active" })).not.toContainText("—");

      // Publish new policy version on /psm/policy (BR-PSM-028).
      await sidebar(page).getByRole("link", { name: "Policy", exact: true }).click();
      await page.getByRole("button", { name: "Publish new version" }).click();
      const polDialog = page.getByRole("dialog");
      const polCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/policy") && r.request().method() === "POST",
      );
      await polDialog.getByRole("button", { name: "Publish policy" }).click();
      expect((await polCreated).status()).toBe(201);
      await expect(polDialog).toBeHidden();
    });
  });

  test.describe("7. GRN inspection, discrepancy report & resolution, receipt confirmation, and dashboard notifications (PSM-UC-002, 020, 028, 032, 035)", () => {
    test("faculty records GRN and discrepancy, ps_admin resolves discrepancy, faculty confirms receipt and sees lifecycle notifications", async ({
      browser,
    }) => {
      await ensureActiveRole(browser, "psmRequester");
      const reqCtx = await browser.newContext(signedInAs("psmRequester"));
      const reqPage = await reqCtx.newPage();
      let caseNumber = "";

      try {
        await reqPage.goto("/");
        await actAs(reqPage, "psmRequester");
        await openModuleNav(reqPage, "Procurement & Stores");
        await sidebar(reqPage).getByRole("link", { name: "Receipts & Discrepancies", exact: true }).click();

        // PSM-UC-028: Inspect Delivery and Record GRN (received 4, accepted 3, rejected 1).
        await reqPage.getByRole("button", { name: "Record GRN" }).click();
        const grnDialog = reqPage.getByRole("dialog");
        await grnDialog.getByLabel("Purchase Order ID").fill(String(state.directPoId));
        await grnDialog.getByLabel("Received quantity").fill("4");
        await grnDialog.getByLabel("Accepted quantity").fill("3");
        await grnDialog.getByLabel("Rejected quantity").fill("1");
        const grnCreated = reqPage.waitForResponse(
          (r) => r.url().includes("/api/v1/psm/grns") && r.request().method() === "POST",
        );
        await grnDialog.getByRole("button", { name: "Save GRN" }).click();
        const grnRes = await grnCreated;
        expect(grnRes.status()).toBe(201);
        const grnBody = (await grnRes.json()) as { id: number; grn_number: string };
        state.grnId = grnBody.id;
        state.grnNumber = grnBody.grn_number;
        await expect(grnDialog).toBeHidden();

        // PSM-UC-020: Report Delivery Discrepancy and Initiate Return or Replacement.
        await reqPage.getByRole("button", { name: "Report discrepancy" }).click();
        const discDialog = reqPage.getByRole("dialog");
        await discDialog.getByLabel("GRN ID").fill(String(state.grnId));
        await discDialog.getByLabel("Affected quantity").fill("1");
        await discDialog.getByLabel("Description").fill("1 unit damaged in transit");
        const discCreated = reqPage.waitForResponse(
          (r) => r.url().includes("/api/v1/psm/discrepancies") && r.request().method() === "POST",
        );
        await discDialog.getByRole("button", { name: "Log discrepancy" }).click();
        const discRes = await discCreated;
        expect(discRes.status()).toBe(201);
        caseNumber = ((await discRes.json()) as { case_number: string }).case_number;
        await expect(discDialog).toBeHidden();
      } finally {
        await reqCtx.close();
      }

      // PSM-UC-032: Coordinate Vendor Discrepancy Resolution as ps_admin.
      await ensureActiveRole(browser, "psAdmin");
      const psCtx = await browser.newContext(signedInAs("psAdmin"));
      const psPage = await psCtx.newPage();
      try {
        await psPage.goto("/");
        await actAs(psPage, "psAdmin");
        await openModuleNav(psPage, "Procurement & Stores");
        await sidebar(psPage).getByRole("link", { name: "Receipts & Discrepancies", exact: true }).click();
        const caseRow = psPage.getByRole("row").filter({ hasText: caseNumber });
        const resolved = psPage.waitForResponse(
          (r) => r.url().includes("/discrepancies/") && r.url().includes("/resolve"),
        );
        await caseRow.getByRole("button", { name: "Resolve" }).click();
        expect((await resolved).status()).toBe(200);
        await psPage.reload();
        await expect(psPage.getByRole("row").filter({ hasText: caseNumber })).toContainText("resolved");
      } finally {
        await psCtx.close();
      }

      // PSM-UC-002: Confirm Delivery Receipt as faculty requester & PSM-UC-035: Verify rendered lifecycle notifications on /psm/dashboard.
      const reqCtx2 = await browser.newContext(signedInAs("psmRequester"));
      const reqPage2 = await reqCtx2.newPage();
      try {
        await reqPage2.goto("/");
        await actAs(reqPage2, "psmRequester");
        await openModuleNav(reqPage2, "Procurement & Stores");
        await sidebar(reqPage2).getByRole("link", { name: "Receipts & Discrepancies", exact: true }).click();
        const grnRow = reqPage2.getByRole("row").filter({ hasText: state.grnNumber });
        const confirmed = reqPage2.waitForResponse(
          (r) => r.url().includes(`/api/v1/psm/grns/${state.grnId}/confirm`) && r.request().method() === "POST",
        );
        await grnRow.getByRole("button", { name: "Confirm receipt" }).click();
        expect((await confirmed).status()).toBe(200);
        await reqPage2.reload();
        await expect(reqPage2.getByRole("row").filter({ hasText: state.grnNumber })).toContainText(
          "confirmed",
        );
        await expect(reqPage2.getByRole("row").filter({ hasText: state.grnNumber })).toContainText(
          "Yes",
        );

        // PSM-UC-035: Automated lifecycle notifications rendered on Dashboard.
        await sidebar(reqPage2).getByRole("link", { name: "Dashboard", exact: true }).click();
        await expect(reqPage2.getByRole("heading", { name: "Recent Notifications" })).toBeVisible();
        await expect(
          reqPage2.getByText(`Delivery receipt confirmed for ${state.grnNumber}`),
        ).toBeVisible();
      } finally {
        await reqCtx2.close();
      }
    });
  });

  test.describe("8. Accounts Admin three-way match, payment release, and financial report (PSM-UC-013, 015, 029)", () => {
    test.use(signedInAs("psmAccounts"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmAccounts");
    });

    test("Accounts Admin records invoice, performs three-way match, releases payment, and generates financial report", async ({
      page,
    }) => {
      const invoiceNumber = uniqueName("INV-E2E").replace(/\s+/g, "-");

      await page.goto("/");
      await actAs(page, "psmAccounts");
      await openModuleNav(page, "Procurement & Stores");
      await sidebar(page).getByRole("link", { name: "Invoices & Payments", exact: true }).click();

      // PSM-UC-013: Submit and Verify Vendor Invoice (Three-Way Match) for 3 confirmed units @ 5000 = 15000.
      await page.getByRole("button", { name: "Record invoice" }).click();
      const invDialog = page.getByRole("dialog");
      await invDialog.getByLabel("Purchase Order ID").fill(String(state.directPoId));
      await invDialog.getByLabel("Invoice number").fill(invoiceNumber);
      await invDialog.getByLabel("Billed quantity").fill("3");
      await invDialog.getByLabel("Billed amount").fill("15000.00");
      const invCreated = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/invoices") && r.request().method() === "POST",
      );
      await invDialog.getByRole("button", { name: "Save invoice" }).click();
      expect((await invCreated).status()).toBe(201);
      await expect(invDialog).toBeHidden();

      const invRow = page.getByRole("row").filter({ hasText: invoiceNumber });
      const verified = page.waitForResponse(
        (r) => r.url().includes("/verify") && r.request().method() === "POST",
      );
      await invRow.getByRole("button", { name: "Verify match" }).click();
      expect((await verified).status()).toBe(200);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: invoiceNumber })).toContainText("verified");

      // PSM-UC-029: Process and Release Vendor Payment.
      const paid = page.waitForResponse(
        (r) => r.url().includes("/pay") && r.request().method() === "POST",
      );
      await page.getByRole("row").filter({ hasText: invoiceNumber }).getByRole("button", { name: "Release payment" }).click();
      expect((await paid).status()).toBe(201);
      await page.reload();
      await expect(page.getByRole("row").filter({ hasText: invoiceNumber })).toContainText("paid");

      // PSM-UC-015: Generate Financial Reports.
      await sidebar(page).getByRole("link", { name: "Reports", exact: true }).click();
      await page.getByRole("textbox", { name: "Report type" }).click();
      await page.getByRole("option", { name: "financial" }).click();
      const finRep = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/reports/generate") && r.request().method() === "POST",
      );
      await page.getByRole("button", { name: "Generate report" }).click();
      expect((await finRep).status()).toBe(200);
      await expect(page.getByText(/generated financial report/i)).toBeVisible();
    });
  });

  test.describe("9. Auditor read-only audit trail inspection and filtering (PSM-UC-014)", () => {
    test.use(signedInAs("psmAuditor"));

    test.beforeAll(async ({ browser }) => {
      await ensureActiveRole(browser, "psmAuditor");
    });

    test("Auditor inspects and filters the audit trail by entity", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmAuditor");
      await openModuleNav(page, "Procurement & Stores");

      // PSM-UC-014: Access Internal and Statutory Audit Records.
      await sidebar(page).getByRole("link", { name: "Audit Trail", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Audit Trail", level: 2 })).toBeVisible();
      await expect(page.getByRole("row").nth(1)).toBeVisible();

      const filtered = page.waitForResponse(
        (r) => r.url().includes("/api/v1/psm/audit") && r.url().includes("target_type=invoice"),
      );
      await page.getByRole("textbox", { name: "Filter by entity" }).click();
      await page.getByRole("option", { name: "invoice" }).click();
      expect((await filtered).status()).toBe(200);
      await expect(page.getByRole("row").filter({ hasText: "payment.released" }).first()).toBeVisible();
    });
  });
});
