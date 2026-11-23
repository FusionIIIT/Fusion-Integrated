import { expect, sidebar, test, uniqueName } from "../support/test";
import {
  assignDirector, choose, ensureOffice, go, hasStatus, modal, NAMES, openApp, person, seat, submit,
  submitNew,
} from "./flow";

const TITLE = uniqueName("E2E Office watch");
let REF = "";

test.describe.serial("pms: the office watches, reports and configures", () => {
  test.beforeAll(async () => {
    await ensureOffice();
  });

  // UC-PMS-027 BR-PMS-033
  test("PCC_ADMIN moves a review only after its Director leaves the roster", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant");
    const drawer = await submitNew(page, TITLE);
    REF = (await drawer.textContent())?.match(/PMS-\d{4}-\d{5}/)?.[0] ?? "";
    expect(REF).not.toBe("");
    await close();
    await assignDirector(browser, TITLE, "pmsDirector3");

    const pcc = await seat(browser, "pmsPcc");
    await go(pcc.page, "pmsPcc", "Oversight");
    await pcc.page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    let seen = await openApp(pcc.page, TITLE);
    await expect(seen.getByRole("button", { name: "Reassign Director" })).toHaveCount(0);
    await go(pcc.page, "pmsPcc", "Directors");
    const row = pcc.page.getByRole("row").filter({ hasText: NAMES.pmsDirector3 });
    await row.getByRole("button", { name: "Remove" }).click();
    await submit(pcc.page, "Remove", /\/directors\/\d+\/end$/);
    await expect(row).toHaveCount(0);
    await pcc.close();

    await assignDirector(browser, TITLE, "pmsDirector2", "Reassign Director");
    const again = await seat(browser, "pmsPcc");
    await go(again.page, "pmsPcc", "Oversight");
    await again.page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    seen = await openApp(again.page, TITLE);
    await seen.getByRole("tab", { name: "Decisions" }).click();
    await expect(seen.getByText(new RegExp(NAMES.pmsDirector2)).first()).toBeVisible();
    await again.close();
  });

  // UC-PMS-016 PMS-CFR-050
  test("the review deadline is tracked against the Director now responsible", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Deadlines & Escalations");
    const row = page.getByRole("row").filter({ hasText: REF });
    await expect(row).toContainText(NAMES.pmsDirector2);
    await expect(row).toContainText("Review");
    await close();
  });

  // UC-PMS-028 PMS-CFR-080
  test("PCC_ADMIN reads and exports the audit log", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Audit Log");
    await page.getByRole("textbox", { name: "Action starts with" }).fill("application.submit");
    await expect(page.getByRole("row").filter({ hasText: REF }).first()).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export CSV" }).click();
    expect((await download).suggestedFilename()).toMatch(/\.csv$/);
    await close();
  });

  // UC-PMS-024 PMS-CFR-075
  test("PCC_ADMIN runs, exports and schedules a system-wide report", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Reports");
    await expect(page.getByRole("row").filter({ hasText: REF })).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: "Export CSV" }).click();
    expect((await download).suggestedFilename()).toBe("pms-status.csv");
    const name = uniqueName("E2E weekly status");
    await page.getByRole("button", { name: "Save and schedule" }).click();
    await modal(page).getByRole("textbox", { name: "Name" }).fill(name);
    await choose(page, modal(page), "Schedule", "Weekly");
    await submit(page, "Save", /\/report-definitions$/, 201);
    await expect(page.getByRole("row").filter({ hasText: name })).toBeVisible();
    await close();
  });

  // UC-PMS-030 PMS-CFR-077
  test("the applicant's report holds only their own applications and cannot be exported", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant");
    await go(page, "pmsApplicant", "Reports");
    await expect(page.getByRole("row").filter({ hasText: REF })).toBeVisible();
    await expect(page.getByRole("button", { name: "Export CSV" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-031 UC-PMS-032 PMS-CFR-078
  test("the Director reports on and oversees their own work, with no office actions", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsDirector2");
    await go(page, "pmsDirector2", "Reports");
    await expect(page.getByRole("row").filter({ hasText: REF })).toBeVisible();
    await sidebar(page).getByRole("link", { name: "Oversight" }).click();
    await page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    const drawer = await openApp(page, TITLE);
    await hasStatus(drawer, "under review");
    await expect(drawer.getByRole("button", { name: /Assign|Reassign/ })).toHaveCount(0);
    await close();
  });

  // UC-PMS-025 PMS-CFR-085
  test("PCC_ADMIN publishes a new settings version", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Settings");
    await page.getByRole("textbox", { name: /Alert days/ }).fill("30, 15, 5");
    const publish = page.getByRole("button", { name: /^Publish version \d+$/ });
    const answered = page.waitForResponse((r) => r.url().endsWith("/api/v1/pms/policy")
      && r.request().method() === "POST");
    await publish.click();
    expect((await answered).status()).toBe(201);
    await expect(page.getByText(/^Version \d+ is in effect\.$/)).toBeVisible();
    await close();
  });

  // UC-PMS-026 PMS-CFR-087
  test("PCC_ADMIN keeps a panel attorney's areas up to date", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Attorney Panel");
    await page.getByRole("button", { name: "Add panel attorney" }).click();
    await person(page, modal(page), "Person", "pmsAttorney");
    await modal(page).getByRole("textbox", { name: "Technical areas" }).click();
    await page.getByRole("option", { name: "E2E Materials" }).click();
    await submit(page, "Save", /\/attorney-panel$/, 201);
    await expect(page.getByRole("row").filter({ hasText: NAMES.pmsAttorney })).toContainText("e2e_materials");
    await close();
  });
});
