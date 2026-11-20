import { expect, signedInAs, test } from "../support/test";
import {
  type Api, apiAs, applied, approvedCompany, openScreen, profileCompleted, publishedPosting, registered,
} from "./setup";

test.describe("placement: a student's own flows", () => {
  test.describe.configure({ mode: "serial" });
  test.use(signedInAs("applicant"));

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
  });

  test("PC-UC-001, PC-UC-023: the student opens the profile and its structured resume", async ({ page }) => {
    await openScreen(page, "My Profile");
    await expect(page.getByRole("heading", { name: "My Profile", level: 2 })).toBeVisible();
    await expect(page.getByText("Structured resume")).toBeVisible();
    await expect(page.getByText(/^CPI \d/)).toBeVisible();

    await page.getByRole("button", { name: "Add document" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Drive link" })
      .fill("https://drive.google.com/file/d/1E2eCertificateFileId0123456789/view");
    await dialog.getByRole("textbox", { name: "Title" }).fill("E2E certificate");
    await dialog.getByRole("button", { name: "Add document" }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole("link", { name: "E2E certificate" }).first()).toBeVisible();
  });

  test("PC-UC-002, PC-UC-003: the student browses, checks eligibility and applies", async ({ page }) => {
    const posting = await publishedPosting(office, companyId);
    await openScreen(page, "Opportunities");
    await page.getByText(posting.title, { exact: true }).click();
    const drawer = page.getByRole("dialog");
    await expect(drawer.getByText("You are eligible for this posting")).toBeVisible();

    const sent = page.waitForResponse((r) =>
      r.url().endsWith("/placement/applications/apply") && r.request().method() === "POST");
    await drawer.getByRole("button", { name: "Apply" }).click();
    expect((await sent).status()).toBe(201);
  });

  test("PC-UC-004: the student tracks the application", async ({ page }) => {
    const posting = await publishedPosting(office, companyId);
    await applied(student, posting.id);
    await openScreen(page, "My Applications");
    const row = page.getByRole("row").filter({ hasText: posting.title });
    await expect(row).toContainText(/submitted/i);
  });

  test("PC-UC-005: the student answers an offer before its deadline", async ({ page }) => {
    const posting = await publishedPosting(office, companyId);
    const app = await applied(student, posting.id);
    await office.post(`/applications/${app.id}/transition`, { to_status: "shortlisted" });
    await office.post("/offers/issue", { application_id: app.id });

    await openScreen(page, "My Offers");
    const card = page.getByRole("article", { name: posting.title });
    await card.getByRole("button", { name: "Decline" }).click();
    const responded = page.waitForResponse((r) => r.url().includes("/respond"));
    await page.getByRole("dialog").getByRole("button", { name: "Decline" }).click();
    expect((await responded).status()).toBe(200);
    await expect(page.getByText("Past offers")).toBeVisible();
  });

  test("PC-UC-024: the student reads anonymised statistics for a season", async ({ page }) => {
    await openScreen(page, "Reports");
    await expect(page.getByRole("heading", { name: "Placement Statistics", level: 2 }))
      .toBeVisible();
    await expect(page.getByRole("textbox", { name: "Season" })).toBeVisible();
    await expect(page.getByText("Applications CSV")).toHaveCount(0);
  });
});
