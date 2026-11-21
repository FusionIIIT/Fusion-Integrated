import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import type { Page } from "@playwright/test";

import { type AccountKey } from "../accounts";
import { stateFile } from "../support/session";
import { actAs, expect, signedInAs, test as base } from "../support/test";

const API = "/api/v1/hreis";
const test = base.extend<{ actor: (key: AccountKey) => Promise<Page> }>({
  actor: async ({ browser, baseURL }, use) => {
    const pages = new Map<AccountKey, Page>();
    const problems: string[] = [];
    await use(async (key) => {
      if (!pages.has(key)) {
        const context = await browser.newContext({ baseURL, storageState: stateFile(key) });
        const page = await context.newPage();
        // Actor pages get the same runtime guards as the primary employee page.
        page.on("pageerror", (error) => problems.push(error.message));
        page.on("console", (message) => {
          if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) {
            problems.push(message.text());
          }
        });
        page.on("response", (response) => {
          if (response.url().includes("/api/") && response.status() >= 500) {
            problems.push(`${response.status()} ${response.url()}`);
          }
        });
        await page.goto("/");
        await actAs(page, key);
        pages.set(key, page);
      }
      return pages.get(key)!;
    });
    for (const page of pages.values()) await page.context().close();
    expect(problems, "actor page runtime, console and server errors").toEqual([]);
  },
});
test.use(signedInAs("hrEmployee"));
test.beforeAll(() => {
  if (process.env.HREIS_E2E_SYNTHETIC !== "1") {
    throw new Error("Run bash client/e2e/hreis/run-isolated.sh with a synthetic IAM; workflow tests require disposable fixtures.");
  }
});

test("HR-UC-001/002: HR creates an official record, employee reads it, and stale edits fail", async ({ actor }) => {
  const employee = await actor("hrAuthority");
  const me = await employee.request.get("/api/v1/me");
  const id = (await me.json()).user.id as number;
  const hr = await actor("hrAdmin");
  await hr.goto("/hreis/administration");
  await hr.getByRole("button", { name: "Create employee record" }).click();
  await hr.getByRole("textbox", { name: "Employee directory ID" }).fill(String(id));
  await hr.getByRole("textbox", { name: "Department", exact: true }).fill("CSE");
  await hr.getByRole("textbox", { name: "Designation snapshot" }).fill("SYNTHETIC AUTHORITY");
  const saved = await submit(hr, "/service-records/", "Save record", 201);
  await employee.goto("/hreis/my-record");
  await expect(employee.getByText("SYNTHETIC AUTHORITY", { exact: true })).toBeVisible();
  await expect(employee.getByRole("button", { name: "Save record" })).toHaveCount(0);
  const session = await hr.request.get("/api/v1/me");
  const csrf = (await session.json()).csrf_token as string;
  const stale = await hr.request.patch(`${API}/service-records/${saved.id}/`, {
    data: { expected_revision: saved.revision + 1, retirement_status: "stale synthetic value" },
    headers: { "X-CSRF-Token": csrf, "Idempotency-Key": `stale-${saved.id}` },
  });
  expect(stale.status()).toBe(409);
  expect((await (await employee.request.get(`${API}/service-records/me/`)).json()).retirement_status).toBe("");
});

test("HR-UC-003: cookie writes require CSRF and cannot override request ownership", async ({ page }) => {
  const before = await page.request.get(`${API}/requests/`);
  const count = (await before.json()).count;
  const data = { leave_type: "Casual", duration: "1", justification: "Synthetic security probe" };
  const missingCsrf = await page.request.post(`${API}/requests/leave/`, {
    data, headers: { "Idempotency-Key": "no-csrf-synthetic" },
  });
  expect(missingCsrf.status()).toBe(403);
  expect((await missingCsrf.json()).error.message).toContain("CSRF");
  const forged = await post(page, "/requests/leave/", { ...data, user_id: 900099 }, "forged-owner");
  expect(forged.status()).toBe(400);
  expect((await (await page.request.get(`${API}/requests/`)).json()).count).toBe(count);
});

function row(page: Page, id: number) {
  return page.getByRole("row").filter({ has: page.getByRole("cell", { name: `#${id}`, exact: true }) });
}
async function submit(page: Page, endpoint: string, button: string, status = 200) {
  const response = page.waitForResponse((r) =>
    r.url().endsWith(`${API}${endpoint}`) && r.request().method() === "POST");
  await page.getByRole("dialog").getByRole("button", { name: button, exact: true }).click();
  const result = await response;
  expect(result.status(), await result.text()).toBe(status);
  return result.json();
}
async function leave(page: Page, duration = "2") {
  await page.goto("/hreis/leave");
  await page.getByRole("button", { name: "Apply for leave" }).click();
  await page.getByRole("textbox", { name: "Duration (days)" }).fill(duration);
  await page.getByRole("textbox", { name: "Justification" }).fill("Synthetic browser leave");
  return submit(page, "/requests/leave/", "Submit request", 201);
}
async function balance(page: Page) {
  const response = await page.request.get(`${API}/service-records/me/`);
  expect(response.status()).toBe(200);
  return Number((await response.json()).leave_balances.Casual);
}
async function post(page: Page, endpoint: string, data: Record<string, unknown>, key: string) {
  const me = await page.request.get("/api/v1/me");
  expect(me.status()).toBe(200);
  const csrf = (await me.json()).csrf_token as string;
  expect(csrf).toBeTruthy();
  return page.request.post(`${API}${endpoint}`, {
    data, headers: { "Idempotency-Key": key, "X-CSRF-Token": csrf },
  });
}
async function decide(page: Page, id: number, decision: "forward" | "approve" | "reject", reason = "") {
  await page.goto("/hreis/approvals");
  await row(page, id).getByRole("button", { name: "Review", exact: true }).click();
  const drawer = page.getByRole("dialog");
  await drawer.getByRole("textbox", { name: "Authority decision" }).click();
  await page.getByRole("option", { name: decision === "forward" ? "Forward to next authority"
    : decision === "approve" ? "Approve at final authority" : "Reject with reason" }).click();
  if (reason) await drawer.getByRole("textbox", { name: "Decision reason (required for rejection)" }).fill(reason);
  return submit(page, `/requests/${id}/decision/`, "Record decision");
}
async function reviewedClaim(page: Page, hr: Page, first: Page, final: Page,
  family: "ltc" | "cpda", subtype: "advance" | "reimbursement", outcome: "approve" | "reject" = "approve") {
  await page.goto("/hreis/claims");
  await page.getByRole("button", { name: `${family.toUpperCase()} request` }).click();
  if (subtype === "reimbursement") {
    await page.getByRole("textbox", { name: "Request kind" }).click();
    await page.getByRole("option", { name: "Reimbursement", exact: true }).click();
  }
  if (family === "ltc") {
    await page.getByRole("textbox", { name: "Official LTC form reference" }).fill("SYNTHETIC-LTC-FORM");
  } else {
    await page.getByRole("textbox", { name: "Purpose", exact: true }).fill("Synthetic training");
    await page.getByRole("textbox", { name: "Claim amount" }).fill("125.50");
    await page.getByRole("textbox", { name: "Document references (comma-separated)" }).fill("SYNTHETIC-INVOICE");
  }
  const created = await submit(page, "/requests/claims/", "Submit request", 201);
  expect(created.state).toBe("awaiting_hr_verification");
  expect(created.claim_summary.hr_verified).toBe(false);
  // The authority cannot bypass HR verification.
  expect((await post(first, `/requests/${created.id}/decision/`,
    { event: "approve" }, `premature-${created.id}`)).status()).toBe(404);
  await hr.goto("/hreis/requests");
  await row(hr, created.id).getByRole("button", { name: "Verify claim" }).click();
  await submit(hr, `/requests/${created.id}/verify-claim/`, "Record decision", 400);
  await hr.getByRole("textbox", { name: "Document review evidence reference" }).fill("SYNTHETIC-HR-REVIEW");
  await hr.getByRole("textbox", { name: "Eligibility basis" }).fill("Synthetic eligibility attestation");
  const verified = await submit(hr, `/requests/${created.id}/verify-claim/`, "Record decision");
  expect(verified.claim_summary.hr_verified).toBe(true);
  expect(verified.route_total_steps).toBe(2);
  expect((await decide(first, created.id, "forward")).route_step).toBe(1);
  expect((await decide(final, created.id, outcome, "Synthetic insufficient evidence")).state)
    .toBe(outcome === "approve" ? "approved" : "rejected");
  return created.id as number;
}

test("HR-UC-003/004/005: leave forwards, approves once, debits once and notifies its owner", async ({ page, actor }) => {
  const before = await balance(page);
  const created = await leave(page);
  expect(created.route_total_steps).toBe(2);
  expect(await balance(page)).toBe(before);
  const first = await actor("hrReviewer");
  const final = await actor("hrAuthority");
  expect((await final.request.get(`${API}/requests/${created.id}/`)).status()).toBe(404);
  const employeeAttempt = await post(page, `/requests/${created.id}/decision/`,
    { event: "approve" }, `owner-${created.id}`);
  expect(employeeAttempt.status()).toBe(403);
  expect((await decide(first, created.id, "forward")).route_step).toBe(1);
  expect(await balance(page)).toBe(before);
  expect((await decide(final, created.id, "approve")).state).toBe("approved");
  expect(await balance(page)).toBe(before - 2);
  const replay = await post(final, `/requests/${created.id}/decision/`,
    { event: "approve" }, `repeat-${created.id}`);
  expect(replay.status()).toBe(404);
  expect(await balance(page)).toBe(before - 2);
  await page.goto("/hreis/leave");
  await expect(row(page, created.id)).toContainText("Approved");
  await row(page, created.id).getByRole("button", { name: "Details", exact: true }).click();
  const history = page.getByRole("dialog");
  await expect(history.getByText("Workflow history", { exact: true })).toBeVisible();
  await expect(history.getByText("approve — approved", { exact: true })).toBeVisible();
  await expect(history.getByText("Acting role: Registrar", { exact: true })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("leave-approved-history.png"), fullPage: true });
  await page.goto("/hreis/notifications");
  await expect(page.getByText("LEAVE request: approve", { exact: true }).first()).toBeVisible();
});

test("HR-UC-004 rejected leave requires a reason and preserves the balance", async ({ page, actor }) => {
  const before = await balance(page);
  const created = await leave(page, "1");
  const first = await actor("hrReviewer");
  const blank = await post(first, `/requests/${created.id}/decision/`,
    { event: "reject", reason: "" }, `blank-${created.id}`);
  expect(blank.status()).toBe(400);
  expect((await decide(first, created.id, "reject", "Synthetic missing evidence")).state).toBe("rejected");
  expect(await balance(page)).toBe(before);
  await page.goto("/hreis/leave");
  await expect(row(page, created.id)).toContainText("Rejected");
});

test("HR-UC-003 exception: insufficient leave cannot create a request", async ({ page }) => {
  const before = await balance(page);
  await page.goto("/hreis/leave");
  await page.getByRole("button", { name: "Apply for leave" }).click();
  await page.getByRole("textbox", { name: "Duration (days)" }).fill("999");
  await page.getByRole("textbox", { name: "Justification" }).fill("Synthetic overdraw");
  await submit(page, "/requests/leave/", "Submit request", 409);
  await expect(page.getByText("Request could not be submitted")).toBeVisible();
  expect(await balance(page)).toBe(before);
});

for (const family of ["ltc", "cpda"] as const) {
  for (const subtype of ["advance", "reimbursement"] as const) {
    test(`HR-UC-${family === "ltc" ? "009/010/011/012" : "013/014/015/016"}: ${family} ${subtype} through HR, approval and Accountant`, async ({ page, actor }) => {
      const hr = await actor("hrAdmin");
      const first = await actor("hrReviewer");
      const final = await actor("hrAuthority");
      const id = await reviewedClaim(page, hr, first, final, family, subtype);
      const accountant = await actor("hrAccountant");
      expect((await post(page, `/requests/${id}/financial-processing/`,
        {}, `owner-finance-${id}`)).status()).toBe(403);
      await accountant.goto("/hreis/finance");
      await row(accountant, id).getByRole("button", { name: "Verify financial correctness" }).click();
      await accountant.getByRole("textbox", { name: "Financial review evidence reference" }).fill("SYNTHETIC-FINANCE-REVIEW");
      await submit(accountant, `/requests/${id}/financial-review/`, "Record finance review");
      for (const status of ["payment_pending", "paid"] as const) {
        await row(accountant, id).getByRole("button", { name: "Record finance status" }).click();
        if (status === "payment_pending") {
          await submit(accountant, `/requests/${id}/financial-processing/`, "Record external status", 400);
        }
        await accountant.getByRole("textbox", { name: "Financial review evidence reference" }).fill("SYNTHETIC-FINANCE-REVIEW");
        await accountant.getByRole("textbox", { name: "External status reference" }).fill(`SYNTHETIC-EXTERNAL-${status}`);
        if (status === "paid") {
          await accountant.getByRole("textbox", { name: "Status reported by the external system" }).click();
          await accountant.getByRole("option", { name: "paid", exact: true }).click();
        }
        const result = await submit(accountant, `/requests/${id}/financial-processing/`, "Record external status");
        expect(result.claim_summary.payment_status).toBe(status);
        await expect(accountant.getByRole("dialog")).toHaveCount(0);
      }
      await expect(row(accountant, id).getByRole("button", { name: "Record finance status" })).toHaveCount(0);
      const detail = await page.request.get(`${API}/requests/${id}/`);
      const saved = await detail.json();
      expect(saved.state).toBe("financial_processing_recorded");
      expect(saved.claim_summary.status_history).toHaveLength(2);
      expect(saved.claim_summary.payment_status).toBe("paid");
      await page.goto("/hreis/claims");
      await expect(row(page, id)).toContainText("Financial Processing Recorded");
      await row(page, id).getByRole("button", { name: "Details", exact: true }).click();
      await expect(page.getByRole("dialog").getByText("Reported financial status history", { exact: true })).toBeVisible();
      await expect(page.getByRole("dialog").getByText("finance: SYNTHETIC-EXTERNAL-paid", { exact: true })).toBeVisible();
    });
  }
  test(`HR-UC-004: rejected ${family} stays outside the Accountant queue`, async ({ page, actor }) => {
    const hr = await actor("hrAdmin");
    const first = await actor("hrReviewer");
    const final = await actor("hrAuthority");
    const id = await reviewedClaim(page, hr, first, final, family, "advance", "reject");
    const accountant = await actor("hrAccountant");
    await accountant.goto("/hreis/finance");
    await expect(row(accountant, id)).toHaveCount(0);
    expect((await accountant.request.get(`${API}/requests/${id}/`)).status()).toBe(404);
    expect((await post(accountant, `/requests/${id}/financial-processing/`, {
      financial_review_reference: "SYNTHETIC", source_system: "finance",
      external_status_reference: "SYNTHETIC", payment_status: "paid",
    }, `rejected-finance-${id}`)).status()).toBe(404);
    await page.goto("/hreis/claims");
    await expect(row(page, id)).toContainText("Rejected");
  });
}

test("HR-UC-006/007/008: appraisal assignment, scoped review, forwarding and final archive", async ({ page, actor }) => {
  await page.goto("/hreis/appraisals");
  await page.getByRole("button", { name: "Annual appraisal", exact: true }).click();
  await page.getByRole("textbox", { name: "Appraisal period" }).fill(`SYNTHETIC-${Date.now()}`);
  await page.getByRole("textbox", { name: "Completed appraisal form (JSON object)" }).fill('{"summary":"Synthetic teaching evidence"}');
  const created = await submit(page, "/requests/appraisals/", "Submit request", 201);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Annual appraisal", exact: true }).click();
  await submit(page, "/requests/appraisals/", "Submit request", 409);
  await page.getByRole("dialog").getByRole("button", { name: "Cancel", exact: true }).click();
  const hr = await actor("hrAdmin");
  const first = await actor("hrReviewer");
  const final = await actor("hrAuthority");
  const me = await first.request.get("/api/v1/me");
  const reviewerId = (await me.json()).user.id;
  const owner = await page.request.get("/api/v1/me");
  expect((await post(hr, `/requests/${created.id}/assign-reviewers/`,
    { reviewer_user_ids: [(await owner.json()).user.id] }, `self-review-${created.id}`)).status()).toBe(400);
  expect((await final.request.get(`${API}/requests/${created.id}/`)).status()).toBe(404);
  await hr.goto("/hreis/requests");
  await row(hr, created.id).getByRole("button", { name: "Assign reviewers" }).click();
  await hr.getByRole("textbox", { name: "Verified reviewer directory IDs (comma-separated)" }).fill(String(reviewerId));
  expect((await submit(hr, `/requests/${created.id}/assign-reviewers/`, "Record decision")).state).toBe("pending_review");
  for (const [reviewer, state] of [[first, "pending_next_appraisal_authority"], [final, "finalized"]] as const) {
    await reviewer.goto("/hreis/approvals");
    await row(reviewer, created.id).getByRole("button", { name: "Review", exact: true }).click();
    await expect(reviewer.getByRole("dialog").getByText(/Synthetic teaching evidence/).last()).toBeVisible();
    expect((await submit(reviewer, `/requests/${created.id}/appraisal-decision/`, "Record decision")).state).toBe(state);
  }
  await page.goto("/hreis/my-record");
  await expect(page.getByText(/"kind":"appraisal"/)).toContainText('"summary":"Synthetic teaching evidence"');
  await page.goto("/hreis/appraisals");
  await expect(row(page, created.id)).toContainText("Finalized");
});

test("HR-UC-017: malformed policy route is rejected through the editor without server errors", async ({ actor }) => {
  const hr = await actor("hrAdmin");
  await hr.goto("/hreis/administration");
  await hr.getByRole("button", { name: "Record new policy version" }).click();
  await hr.getByRole("textbox", { name: "Policy version", exact: true }).fill("3");
  await hr.getByRole("textbox", { name: "Effective from (ISO 8601 date and time with offset)" })
    .fill(new Date(Date.now() + 86400000 * 5).toISOString());
  await hr.getByRole("textbox", { name: "Approved policy parameters (JSON)" }).fill(JSON.stringify({
    routes: [{ employee_kind: [], department: "CSE", authorities: ["Registrar"] }],
  }));
  const response = hr.waitForResponse((r) => r.url().endsWith(`${API}/policies/`) && r.request().method() === "POST");
  await hr.getByRole("button", { name: "Record immutable policy version" }).click();
  expect((await response).status()).toBe(400);
  await expect(hr.getByText("Could not record HR policy", { exact: true })).toBeVisible();
});

test("HR-UC-017/018: publish a future immutable policy and inspect redacted compliance", async ({ actor }) => {
  const hr = await actor("hrAdmin");
  await hr.goto("/hreis/administration");
  await hr.getByRole("button", { name: "Record new policy version" }).click();
  await hr.getByRole("textbox", { name: "Policy version", exact: true }).fill("2");
  await hr.getByRole("textbox", { name: "Effective from (ISO 8601 date and time with offset)" })
    .fill(new Date(Date.now() + 86400000 * 3).toISOString());
  await hr.getByRole("textbox", { name: "Approved policy parameters (JSON)" }).fill(JSON.stringify({
    routes: [{ employee_kind: "staff", department: "CSE", authorities: ["Registrar"] }],
    eligibility: { staff: { Casual: true } },
  }));
  const response = hr.waitForResponse((r) => r.url().endsWith(`${API}/policies/`) && r.request().method() === "POST");
  await hr.getByRole("button", { name: "Record immutable policy version" }).click();
  expect((await response).status()).toBe(201);
  await expect(hr.getByText("Policy version recorded", { exact: true })).toBeVisible();
  await hr.goto("/hreis/audit");
  await expect(hr.getByText("Request compliance status")).toBeVisible();
  const audit = await hr.request.get(`${API}/audit/`);
  expect((await audit.json()).results.some((event: { action: string }) => event.action === "policy_create")).toBe(true);
  const compliance = await hr.request.get(`${API}/compliance/requests/`);
  for (const item of (await compliance.json()).results) {
    expect(Object.keys(item).sort()).toEqual(["created_at", "family", "id", "state", "submitted_at", "user_id"]);
  }
});

test("HR-UC-019/021/022: real event generation, idempotent dashboard delivery and recipient isolation", async ({ page, actor }) => {
  const created = await leave(page, "1");
  const repo = fileURLToPath(new URL("../../../", import.meta.url));
  execFileSync(resolve(repo, ".venv/bin/python"),
    [resolve(repo, "client/e2e/hreis/fixtures.py"), "events", String(created.id)], { cwd: repo, stdio: "inherit" });
  const first = await actor("hrReviewer");
  await first.goto("/hreis/notifications");
  await expect(first.getByText("HR-EIS action reminder", { exact: true })).toBeVisible();
  await page.goto("/hreis/notifications");
  await expect(page.getByText("HR-EIS policy or deadline notice", { exact: true })).toBeVisible();
  await expect(page.getByText("HR-EIS action reminder", { exact: true })).toHaveCount(0);
  const own = await page.request.get(`${API}/notifications/`);
  const reminder = await first.request.get(`${API}/notifications/`);
  const reminderNote = (await reminder.json()).results.find((n: { title: string }) => n.title === "HR-EIS action reminder");
  expect((await post(page, `/notifications/${reminderNote.id}/read/`, {}, `foreign-${reminderNote.id}`)).status()).toBe(404);
  expect((await post(first, `/notifications/${reminderNote.id}/read/`, {}, `read-${reminderNote.id}`)).status()).toBe(200);
  expect((await own.json()).results.every((n: { id: number }) => n.id !== reminderNote.id)).toBe(true);
  const detail = await page.request.get(`${API}/requests/${created.id}/`);
  expect((await detail.json()).state).toBe("pending_authority");
});
