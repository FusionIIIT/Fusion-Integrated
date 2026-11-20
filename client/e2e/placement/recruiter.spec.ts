import { ACCOUNTS } from "../accounts";
import { expect, test, uniqueName } from "../support/test";
import {
  type Api, apiAs, applied, draftPosting, openScreen, pickNextMonth, profileCompleted,
  recruiterSignedIn, registered,
} from "./setup";

test.describe("placement: a company and its recruiter", () => {
  let office: Api;
  let student: Api;

  test.beforeAll(async () => {
    profileCompleted("applicant");
    office = await apiAs("placementOfficer");
    student = await apiAs("applicant");
    await registered(student);
  });
  test.afterAll(async () => {
    await office.dispose();
    await student.dispose();
  });

  test("PC-UC-014: a company registers itself and waits for approval", async ({ page }) => {
    const name = uniqueName("E2E Self Co");
    await page.goto("/recruiter/login");
    await page.getByRole("button", { name: "Proceed to login" }).click();
    await page.getByRole("link", { name: "Register your company" }).click();
    await page.getByRole("textbox", { name: "Company name" }).fill(name);
    await page.getByRole("textbox", { name: "Contact person" }).fill("R. Mehta");
    await page.getByRole("textbox", { name: "Contact email" }).fill("hr@self.example.test");
    await page.getByRole("button", { name: "Submit registration" }).click();
    await expect(page.getByText("Registration received", { exact: true })).toBeVisible();
    const companies = await office.get("/companies") as {
      results: { name: string; approval_status: string }[] };
    expect(companies.results.find((c) => c.name === name)?.approval_status).toBe("pending");
  });

  test("PC-UC-015: the recruiter submits a posting to the placement office", async ({ page }) => {
    await recruiterSignedIn(page, office);
    await page.goto("/recruiter/postings");
    const title = uniqueName("E2E Role");
    await draftPosting(page, title);

    const row = page.getByRole("row").filter({ hasText: title });
    await row.getByRole("button", { name: "Submit to office" }).click();
    await expect(row).toContainText("With the placement office");
  });

  test("PC-UC-016, PC-UC-021, PC-UC-022: the recruiter shortlists, schedules and offers", async ({ page }) => {
    await recruiterSignedIn(page, office);
    await page.goto("/recruiter/postings");
    const title = uniqueName("E2E Role");
    await draftPosting(page, title);
    const posting = page.getByRole("row").filter({ hasText: title });
    await posting.getByRole("button", { name: "Publish" }).click();
    await expect(posting).toContainText(/published/i);
    // The student's own application is set up through the API; this spec is the recruiter's.
    const mine = await (await page.request.get("/api/v1/placement/postings")).json() as {
      results: { id: number; title: string }[] };
    const postingId = mine.results.find((p) => p.title === title)?.id;
    expect(postingId, "the published posting").toBeDefined();
    await applied(student, postingId as number);

    await openScreen(page, "Applicants", "Recruitment");
    const row = page.getByRole("row").filter({ hasText: ACCOUNTS.applicant.username });
    await row.getByRole("button", { name: "Action" }).click();
    await page.getByRole("menuitem", { name: "Shortlist" }).click();
    await expect(row).toContainText(/shortlisted/i);

    await openScreen(page, "Interviews", "Recruitment");
    await page.getByRole("button", { name: "Schedule a round" }).click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: "Role" }).click();
    await page.getByRole("option", { name: title }).click();
    await pickNextMonth(form, "Starts at");
    await form.getByRole("textbox", { name: "Meeting link" }).fill("https://meet.example/co");
    const scheduled = page.waitForResponse((r) => r.url().endsWith("/interviews/rounds")
      && r.request().method() === "POST");
    await form.getByRole("button", { name: "Schedule" }).click();
    expect((await scheduled).status()).toBe(201);
    await page.getByRole("row").filter({ hasText: title })
      .getByRole("button", { name: "Add candidates" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("checkbox").first().check();
    await dialog.getByRole("button", { name: "Add 1" }).click();
    await expect(dialog).toBeHidden();

    await openScreen(page, "Applicants", "Recruitment");
    await row.getByRole("button", { name: "Action" }).click();
    await page.getByRole("menuitem", { name: "Issue offer" }).click();
    const offered = page.waitForResponse((r) => r.url().endsWith("/offers/issue"));
    await page.getByRole("dialog").getByRole("button", { name: "Issue offer" }).click();
    expect((await offered).status()).toBe(201);
    await expect(row).toContainText(/offer issued/i);
  });
});
