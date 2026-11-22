// Verify ungranted module users see Not found and psm-granted non-office roles see Not available.
import { actAs, expect, signedInAs, test } from "../support/test";

const GUARDED_PSM_PAGES = [
  "stock",
  "transfers",
  "vendors",
  "tenders",
  "purchase-orders",
  "invoices",
  "reports",
  "audit",
  "policy",
];

test.describe("psm: ungranted module refusal", () => {
  test.use(signedInAs("student"));

  for (const path of GUARDED_PSM_PAGES) {
    test(`a student without psm grant opening /psm/${path} sees Not found`, async ({ page }) => {
      await page.goto(`/psm/${path}`);
      await expect(page.getByText(/not found/i)).toBeVisible();
    });
  }
});

test.describe("psm: guarded office pages", () => {
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

  for (const path of GUARDED_PSM_PAGES) {
    test(`a faculty requester opening /psm/${path} is told it is not for them`, async ({ page }) => {
      await page.goto("/");
      await actAs(page, "psmRequester");
      await page.goto(`/psm/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
