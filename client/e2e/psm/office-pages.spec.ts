// Verify ungranted module users see Not found and psm-granted non-office roles see Not available.
import type { Browser } from "@playwright/test";

import { ACCOUNTS, type AccountKey } from "../accounts";
import { actAs, expect, signedInAs, test } from "../support/test";

const ALL_GUARDED_PSM_PAGES = [
  "stock",
  "transfers",
  "vendors",
  "tenders",
  "purchase-orders",
  "receipts",
  "invoices",
  "reports",
  "audit",
  "policy",
];

const NON_RECEIPT_OFFICE_PAGES = ALL_GUARDED_PSM_PAGES.filter((p) => p !== "receipts");

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

test.describe("psm: ungranted module refusal", () => {
  test.use(signedInAs("student"));

  for (const path of ALL_GUARDED_PSM_PAGES) {
    test(`a student without psm grant opening /psm/${path} sees Not found`, async ({ page }) => {
      await page.goto(`/psm/${path}`);
      await expect(page.getByText(/not found/i)).toBeVisible();
    });
  }
});

test.describe("psm: guarded office pages", () => {
  test.use(signedInAs("psmRequester"));

  test.beforeAll(async ({ browser }) => {
    await ensureActiveRole(browser, "psmRequester");
  });

  for (const path of NON_RECEIPT_OFFICE_PAGES) {
    test(`a faculty requester opening /psm/${path} is told it is not for them`, async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmRequester");
      await page.goto(`/psm/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});

test.describe("psm: receipts guard", () => {
  test.use(signedInAs("psmDirector"));

  test.beforeAll(async ({ browser }) => {
    await ensureActiveRole(browser, "psmDirector");
  });

  test("a director without psm.grn.view opening /psm/receipts is told it is not for them", async ({
    page,
  }) => {
    await page.goto("/");
    await actAs(page, "psmDirector");
    await page.goto("/psm/receipts");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
  });
});
