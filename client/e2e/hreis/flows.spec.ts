import { request as requestFactory } from "@playwright/test";

import { actAs, expect, openSidebar, sidebar, signedInAs, test } from "../support/test";
import { stateFile } from "../support/session";

test.describe("HR-EIS employee access", () => {
  test.use(signedInAs("hrEmployee"));

  test("a staff employee can see HR-EIS and their read-only service record", async ({ page }) => {
    await page.goto("/");
    await openSidebar(page);
    await expect(sidebar(page).getByRole("button", { name: "Human Resources" })).toBeVisible();

    await page.goto("/hreis/my-record");
    await expect(page.getByRole("heading", { name: "My Service Record" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create employee record" })).toHaveCount(0);

    await page.goto("/hreis/requests");
    await expect(page.getByRole("heading", { name: "HR Requests" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Apply for leave" })).toBeVisible();
    await expect(page.getByRole("button", { name: "LTC request" })).toBeVisible();
    await expect(page.getByRole("button", { name: "CPDA request" })).toBeVisible();
  });

  test("an employee cannot open administration or query other employees' records", async ({ page }) => {
    await page.goto("/hreis/administration");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("button", { name: "Create employee record" })).toHaveCount(0);
    const me = await page.request.get("/api/v1/me");
    expect(me.status()).toBe(200);
    const userId = ((await me.json()) as { user: { id: number } }).user.id;
    const response = await page.request.get("/api/v1/hreis/service-records/");
    expect(response.status()).toBe(200);
    const records = (await response.json()) as { results: { user_id: number }[] };
    expect(records.results.every((record) => record.user_id === userId)).toBe(true);
  });

  test("employees cannot open the approval or Accountant queue by deep link", async ({ page }) => {
    await page.goto("/hreis/approvals");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    expect((await page.request.get("/api/v1/hreis/requests/approvals/")).status()).toBe(403);

    await page.goto("/hreis/finance");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("button", { name: "Record finance status" })).toHaveCount(0);
  });

  test("employee-specific leave, claim and appraisal routes expose only their own forms", async ({ page }) => {
    await page.goto("/hreis/leave");
    await expect(page.getByRole("heading", { name: "Leave requests" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Apply for leave" })).toBeVisible();
    await expect(page.getByRole("button", { name: "LTC request" })).toHaveCount(0);

    await page.goto("/hreis/claims");
    await expect(page.getByRole("heading", { name: "LTC and CPDA claims" })).toBeVisible();
    await expect(page.getByRole("button", { name: "LTC request" })).toBeVisible();
    await expect(page.getByRole("button", { name: "CPDA request" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Apply for leave" })).toHaveCount(0);

    await page.goto("/hreis/appraisals");
    await expect(page.getByRole("heading", { name: "Annual appraisals" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Annual appraisal" })).toBeVisible();
    await expect(page.getByRole("button", { name: "CPDA request" })).toHaveCount(0);
  });

  test("invalid leave duration is refused without creating a request", async ({ page }) => {
    await page.goto("/hreis/requests");
    await page.getByRole("button", { name: "Apply for leave" }).click();
    const drawer = page.getByRole("dialog");
    await drawer.getByRole("textbox", { name: "Duration (days)" }).fill("-1");
    await drawer.getByRole("textbox", { name: "Justification" }).fill("Invalid duration boundary");
    const rejected = page.waitForResponse((r) =>
      r.url().includes("/api/v1/hreis/requests/leave/") && r.request().method() === "POST");
    await drawer.getByRole("button", { name: "Submit request" }).click();
    expect((await rejected).status()).toBe(400);
    await expect(page.getByText("Request could not be submitted")).toBeVisible();
  });
});

test.describe("HR-EIS student isolation", () => {
  test.use(signedInAs("student"));

  test("a student has neither HR-EIS navigation nor request API access", async ({ page }) => {
    await page.goto("/hreis/requests");
    await expect(page.getByRole("heading", { name: "Not found" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Apply for leave" })).toHaveCount(0);
    const response = await page.request.get("/api/v1/hreis/requests/");
    expect(response.status()).toBe(403);
  });
});

test.describe("HR-EIS administrator", () => {
  test.use(signedInAs("hrAdmin"));

  test("an HR administrator sees record management, policy governance and audit", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "hrAdmin");
    await page.goto("/hreis/administration");
    await expect(page.getByRole("heading", { name: "HR Administration" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Create employee record" })).toBeVisible();
    await expect(page.getByText("No assumed policy defaults")).toBeVisible();

    await page.goto("/hreis/audit");
    await expect(page.getByRole("heading", { name: "HR Audit" })).toBeVisible();
    const response = await page.request.get("/api/v1/hreis/audit/");
    expect(response.status()).toBe(200);
  });

  test("HR can inspect redacted historical request statuses but not private forms", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "hrAdmin");
    await page.goto("/hreis/audit");
    await expect(page.getByText("Request compliance status", { exact: true })).toBeVisible();

    const response = await page.request.get("/api/v1/hreis/compliance/requests/");
    expect(response.status()).toBe(200);
    const payload = (await response.json()) as {
      results: Record<string, unknown>[];
    };
    const allowed = ["created_at", "family", "id", "state", "submitted_at", "user_id"];
    for (const summary of payload.results) {
      expect(Object.keys(summary).sort()).toEqual(allowed);
      expect(summary).not.toHaveProperty("payload");
      expect(summary).not.toHaveProperty("appraisal_summary");
      expect(summary).not.toHaveProperty("claim_summary");
    }
  });

  test("HR updates a synthetic service record, which its employee can then read", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "hrAdmin");
    await page.goto("/hreis/administration");
    await expect(page.getByRole("heading", { name: "HR Administration" })).toBeVisible();

    const employeeApi = await requestFactory.newContext({
      baseURL: new URL(page.url()).origin,
      storageState: stateFile("hrEmployee"),
    });
    try {
      const me = await employeeApi.get("/api/v1/me");
      expect(me.status()).toBe(200);
      const employeeId = ((await me.json()) as { user: { id: number } }).user.id;

      const list = await page.request.get("/api/v1/hreis/service-records/");
      expect(list.status()).toBe(200);
      const records = (await list.json()) as {
        results: { user_id: number; revision: number }[];
      };
      let before = records.results.find((record) => record.user_id === employeeId);

      if (!before) {
        await page.getByRole("button", { name: "Create employee record" }).click();
        const drawer = page.getByRole("dialog");
        await drawer.getByRole("textbox", { name: "Employee directory ID" })
          .fill(String(employeeId));
        await drawer.getByRole("textbox", { name: "Department" }).fill("CSE");
        await drawer.getByRole("textbox", { name: "Designation snapshot" })
          .fill("Synthetic Staff");
        const created = page.waitForResponse((r) =>
          r.url().endsWith("/api/v1/hreis/service-records/")
            && r.request().method() === "POST");
        await drawer.getByRole("button", { name: "Save record" }).click();
        const response = await created;
        expect(response.status()).toBe(201);
        before = (await response.json()) as { user_id: number; revision: number };
      }

      const row = page.getByRole("row").filter({ hasText: `#${employeeId}` });
      await expect(row).toBeVisible();
      await row.getByRole("button", { name: "Edit" }).click();
      const retirementStatus = `A9 synthetic check ${Date.now()}`;
      const drawer = page.getByRole("dialog");
      await drawer.getByRole("textbox", { name: "Retirement status" })
        .fill(retirementStatus);
      const updated = page.waitForResponse((r) =>
        r.url().includes("/api/v1/hreis/service-records/")
          && r.request().method() === "PATCH");
      await drawer.getByRole("button", { name: "Save record" }).click();
      const response = await updated;
      expect(response.status()).toBe(200);
      const snapshot = (await response.json()) as { revision: number };
      expect(snapshot.revision).toBeGreaterThan(before.revision);

      const own = await employeeApi.get("/api/v1/hreis/service-records/me/");
      expect(own.status()).toBe(200);
      expect(((await own.json()) as { retirement_status: string }).retirement_status)
        .toBe(retirementStatus);

      const audit = await page.request.get("/api/v1/hreis/audit/");
      expect(audit.status()).toBe(200);
      const events = (await audit.json()) as { results: { action: string }[] };
      expect(events.results.some((event) => event.action === "update")).toBe(true);
    } finally {
      await employeeApi.dispose();
    }
  });
});
