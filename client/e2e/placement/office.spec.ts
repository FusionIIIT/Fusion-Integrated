import { actAs, expect, signedInAs, test, uniqueName } from "../support/test";
import {
  type Api, apiAs, applied, approvedCompany, openScreen, postingBody, profileCompleted, publishedPosting,
  registered,
} from "./setup";

test.describe("placement: the placement officer's flows", () => {
  test.use(signedInAs("placementOfficer"));

  let office: Api;
  let student: Api;
  let companyId: number;

  test.beforeAll(async () => {
    profileCompleted("applicant");
    office = await apiAs("placementOfficer");
    student = await apiAs("applicant");
    companyId = await approvedCompany(office);
    await registered(student);
  });
  test.afterAll(async () => {
    await office.dispose();
    await student.dispose();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await actAs(page, "placementOfficer");
  });

  test("PC-UC-006: the officer publishes a draft posting", async ({ page }) => {
    const draft = await office.post("/postings", postingBody({ company_id: companyId }));
    await openScreen(page, "Opportunities");
    await page.getByText(String(draft.title), { exact: true }).click();
    const published = page.waitForResponse((r) => r.url().endsWith("/publish"));
    await page.getByRole("dialog").getByRole("button", { name: "Publish this posting" }).click();
    expect((await published).status()).toBe(200);
    await expect(page.getByRole("row").filter({ hasText: String(draft.title) }))
      .toContainText(/published/i);
  });

  test("PC-UC-008: the officer filters applications and moves one to review", async ({ page }) => {
    const posting = await publishedPosting(office, companyId);
    await applied(student, posting.id);
    await openScreen(page, "Applications");
    const row = page.getByRole("row").filter({ hasText: posting.title });
    await row.getByRole("button", { name: "Action" }).click();
    const moved = page.waitForResponse((r) => r.url().includes("/transition"));
    await page.getByRole("menuitem", { name: "Move to review" }).click();
    expect((await moved).status()).toBe(200);
    await expect(row).toContainText(/under review/i);
  });

  test("PC-UC-009: the officer puts a shortlisted candidate into an interview round", async ({ page }) => {
    const posting = await publishedPosting(office, companyId);
    const app = await applied(student, posting.id);
    await office.post(`/applications/${app.id}/transition`, { to_status: "shortlisted" });
    await office.post("/interviews/rounds", {
      posting_id: posting.id, mode: "online", meeting_url: "https://meet.example/e2e",
      starts_at: new Date(Date.now() + 2 * 864e5).toISOString() });

    await openScreen(page, "Interviews");
    await page.getByRole("row").filter({ hasText: posting.title })
      .getByRole("button", { name: "Add candidates" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("checkbox").first().check();
    const added = page.waitForResponse((r) => r.url().endsWith("/candidates"));
    await dialog.getByRole("button", { name: "Add 1" }).click();
    expect((await added).status()).toBe(201);
    const after = await office.get(`/applications?posting=${posting.id}`) as {
      results: { status: string }[] };
    expect(after.results[0]?.status).toBe("interview_scheduled");
  });

  test("PC-UC-010: the officer corrects a placement record and its history keeps the old value", async ({ page }) => {
    const userId = 900000 + Math.floor(Math.random() * 90000);
    await office.post("/records/off-campus", {
      season: "2026-27", user_id: userId, company_id: companyId, ctc_lpa: "9.00" });
    await openScreen(page, "Placement Records");
    const row = page.getByRole("row").filter({ hasText: `#${userId}` });
    await row.getByRole("button", { name: "Correct" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Package (LPA)" }).fill("11.5");
    await dialog.getByRole("textbox", { name: "Reason" }).fill("Revised offer letter.");
    await dialog.getByRole("button", { name: "Save correction" }).click();
    await expect(row).toContainText("11.50");
    await row.getByRole("button", { name: "History" }).click();
    await expect(page.getByText("Revised offer letter.")).toBeVisible();
  });

  test("PC-UC-011: the officer reads the reports, salary bands and trends", async ({ page }) => {
    await openScreen(page, "Reports");
    await expect(page.getByRole("heading", { name: "Placement Reports", level: 2 })).toBeVisible();
    await expect(page.getByText("Salary package distribution")).toBeVisible();
    await expect(page.getByText("Trends across seasons")).toBeVisible();
  });

  test("PC-UC-020: the officer publishes an announcement", async ({ page }) => {
    const title = uniqueName("E2E drive");
    await openScreen(page, "Announcements");
    await page.getByRole("button", { name: /new announcement|publish/i }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Title" }).fill(title);
    await dialog.getByRole("textbox", { name: "Body" }).fill("Hall 2, 10 am.");
    const sent = page.waitForResponse((r) =>
      r.url().endsWith("/placement/announcements") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: /publish/i }).click();
    expect((await sent).status()).toBe(201);
    await expect(page.getByText(title)).toBeVisible();
  });
});
