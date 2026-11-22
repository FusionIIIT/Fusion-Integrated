import type { Browser, Page, Response } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName } from "../support/test";

const OFFERING = "cof_000b15335a733ab06119a0b2ec528564dfbf2d9084e0d849bb461a458e141b5f";
interface CourseRow { id: number; external_offering_key: string }

async function selectDemoCourse(page: Page, key: AccountKey, route: "My Courses" | "Teaching" | "Grading") {
  await page.goto("/");
  await actAs(page, key);
  await openModuleNav(page, "Course Management");
  const loaded = page.waitForResponse((response) => response.url().includes("/api/v1/lms/courses/")
    && !/\/courses\/\d+\//.test(response.url()) && response.request().method() === "GET");
  await sidebar(page).getByRole("link", { name: route, exact: true }).click();
  let response: Response = await loaded;
  let data = await response.json() as { results: CourseRow[]; next: string | null };
  let row = data.results.find((course) => course.external_offering_key === OFFERING);
  while (!row && data.next) {
    const more = page.waitForResponse((result) => result.url().includes("/api/v1/lms/courses/?cursor="));
    await page.getByRole("button", { name: "Load more courses" }).click();
    response = await more;
    data = await response.json() as { results: CourseRow[]; next: string | null };
    row = data.results.find((course) => course.external_offering_key === OFFERING);
  }
  expect(row, "synthetic source-backed offering is linked to this acting role").toBeDefined();
  await page.getByLabel("Course", { exact: true }).selectOption(String(row?.id));
  if (!row) throw new Error("Synthetic course association is missing");
  return row.id;
}

function localTime(afterSeconds: number) {
  const now = new Date(Date.now() + afterSeconds * 1000);
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 19);
}

async function chooseLoadedCourse(page: Page, id: number) {
  const picker = page.getByLabel("Course", { exact: true });
  await expect(picker).toBeVisible();
  while (await picker.locator(`option[value="${id}"]`).count() === 0) {
    const previous = await picker.locator("option").count();
    await page.getByRole("button", { name: "Load more courses", exact: true }).click();
    await expect.poll(() => picker.locator("option").count()).toBeGreaterThan(previous);
  }
  await picker.selectOption(String(id));
}

async function anotherActor(browser: Browser, key: AccountKey, problems: string[]) {
  const context = await browser.newContext(signedInAs(key));
  const page = await context.newPage();
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error" && !message.text().startsWith("Failed to load resource")) problems.push(message.text());
  });
  page.on("response", (response) => {
    if (response.url().includes("/api/") && response.status() >= 500) problems.push(`${response.status()} ${response.url()}`);
  });
  return { page, context };
}

test.describe("lms: complete course journeys", () => {
  test.use(signedInAs("lmsFaculty"));
  test("UC-LMS-001 through UC-LMS-015: publication, submissions, grading and scheduled release", async ({ page, browser }) => {
    test.setTimeout(240_000);
    const problems: string[] = [];
    const student = await anotherActor(browser, "lmsStudent", problems);
    const ta = await anotherActor(browser, "lmsTa", problems);
    const observer = await anotherActor(browser, "lmsObserver", problems);
    const note = uniqueName("Course note");
    const section = uniqueName("Course unit");
    const news = uniqueName("Course announcement");
    const correctedFeedback = uniqueName("Corrected released feedback");
    const titles = [uniqueName("Text exercise"), uniqueName("File exercise"), uniqueName("Link exercise")];
    let studentCourseId = 0;
    try {
      await test.step("UC-LMS-001/002: faculty configures course details", async () => {
        await selectDemoCourse(page, "lmsFaculty", "Teaching");
        await page.getByLabel("Syllabus", { exact: true }).fill("Synthetic course syllabus for the browser journey");
        await page.getByLabel("Schedule", { exact: true }).fill("Weekly synthetic schedule");
        const saved = page.waitForResponse((response) => /\/lms\/courses\/\d+\/$/.test(response.url()) && response.request().method() === "PATCH");
        await page.getByRole("button", { name: "Publish course details", exact: true }).click();
        expect((await saved).status()).toBe(200);
        await page.getByLabel("Allow assigned TAs to post announcements").check();
        const policy = page.waitForResponse((response) => response.url().includes("/policy-versions/") && response.request().method() === "POST");
        await page.getByRole("button", { name: "Save TA announcement policy" }).click();
        expect((await policy).status()).toBe(201);
      });
      await test.step("UC-LMS-003/015: faculty organizes and schedules material", async () => {
        await page.getByLabel("Section label").fill(section);
        await page.getByRole("button", { name: "Create section", exact: true }).click();
        await expect(page.getByRole("button", { name: `Edit section ${section}`, exact: true })).toBeVisible();
        await page.getByLabel("Material title").fill(note);
        await page.getByLabel("Material note").fill("Scheduled course material");
        await page.getByLabel("Material section").selectOption({ label: section });
        await page.getByRole("button", { name: "Create material", exact: true }).click();
        const card = page.getByRole("heading", { name: note, exact: true }).locator("..");
        await card.getByLabel("Release at (local time, optional)").fill(localTime(15));
        await card.getByRole("button", { name: "Schedule release", exact: true }).click();
        await expect(card).toContainText("SCHEDULED");
      });
      await test.step("UC-LMS-007/008: faculty creates and publishes all submission types", async () => {
        for (const [index, kind] of ["TEXT", "FILE", "LINK"].entries()) {
          const title = titles[index];
          if (title === undefined) throw new Error("Missing exercise title");
          await page.getByLabel("Assignment title (optional)").fill(title);
          await page.getByLabel("Assignment instructions").fill(`Complete the ${kind} exercise`);
          await page.getByLabel("Assignment due date (local time)").fill(localTime(86_400));
          await page.getByLabel("Assignment submission type").selectOption(kind);
          await page.getByLabel("Points possible").fill("20");
          await page.getByRole("button", { name: "Create assignment draft", exact: true }).click();
          const card = page.getByRole("heading", { name: titles[index], exact: true }).locator("..");
          await expect(card).toContainText("DRAFT");
          if (index === 2) {
            await card.getByLabel("Release at (local time, optional)").fill(localTime(15));
            await card.getByRole("button", { name: "Schedule release", exact: true }).click();
            await expect(card).toContainText("SCHEDULED");
          } else {
            await card.getByRole("button", { name: "Publish now", exact: true }).click();
            await expect(card).toContainText("AVAILABLE");
          }
        }
      });
      await test.step("UC-LMS-004/005/006: TA and Observer read common content", async () => {
        await selectDemoCourse(ta.page, "lmsTa", "My Courses");
        await ta.page.getByLabel("Announcement content").fill(news);
        await ta.page.getByRole("button", { name: "Post announcement", exact: true }).click();
        await expect(ta.page.getByText(news, { exact: true })).toBeVisible();
        await selectDemoCourse(observer.page, "lmsObserver", "My Courses");
        await expect(observer.page.getByText("Synthetic course syllabus for the browser journey", { exact: true })).toBeVisible();
        await expect(observer.page.getByText(news, { exact: true })).toBeVisible();
        await expect(observer.page.getByRole("region", { name: "Course assignments" })).toHaveCount(0);
        await expect(observer.page.getByRole("button", { name: "Post announcement" })).toHaveCount(0);
      });
      await test.step("UC-LMS-009/010/011/015: student downloads and submits released assignments", async () => {
        studentCourseId = await selectDemoCourse(student.page, "lmsStudent", "My Courses");
        await expect.poll(async () => {
          await student.page.reload();
          await chooseLoadedCourse(student.page, studentCourseId);
          try {
            await student.page.getByRole("heading", { name: titles[2], exact: true }).waitFor({ state: "visible", timeout: 2000 });
            return true;
          } catch { return false; }
        }, { timeout: 35_000 }).toBe(true);
        await expect(student.page.getByRole("heading", { name: note, exact: true })).toBeVisible();
        for (const [index, kind] of ["TEXT", "FILE", "LINK"].entries()) {
          const card = student.page.getByRole("heading", { name: titles[index], exact: true }).locator("..");
          await card.getByRole("button", { name: "View assignment", exact: true }).click();
          await expect(card.getByText("Submission status: Missing", { exact: true })).toBeVisible();
          const download = student.page.waitForEvent("download");
          await card.getByRole("button", { name: "Download assignment", exact: true }).click();
          expect((await download).suggestedFilename()).toMatch(/^assignment-\d+\.txt$/);
          if (kind === "TEXT") await card.getByLabel("Submission text").fill("Synthetic text submission");
          if (kind === "FILE") await card.getByLabel("Submission file").setInputFiles({ name: "exercise.txt", mimeType: "text/plain", buffer: Buffer.from("Synthetic file submission") });
          if (kind === "LINK") await card.getByLabel("Submission link").fill("https://example.org/exercise");
          await card.getByRole("button", { name: "Submit assignment", exact: true }).click();
          await expect(card.getByText(/Submission status: Submitted/)).toBeVisible();
          await card.getByRole("button", { name: "Close assignment", exact: true }).click();
        }
      });
      await test.step("UC-LMS-012: TA grades a submission and cannot release it", async () => {
        await selectDemoCourse(ta.page, "lmsTa", "Grading");
        await ta.page.getByLabel("Assignment to grade").selectOption({ label: titles[0] });
        await ta.page.getByLabel(/Points for submission/).fill("15");
        await ta.page.getByLabel(/Feedback for submission/).fill("Synthetic draft feedback");
        await ta.page.getByRole("button", { name: "Save draft grade", exact: true }).click();
        await expect(ta.page.getByText(/Grade DRAFT: 15/)).toBeVisible();
        await expect(ta.page.getByRole("button", { name: /Release grade/ })).toHaveCount(0);
        await student.page.reload();
        await chooseLoadedCourse(student.page, studentCourseId);
        await expect(student.page.getByText("Synthetic draft feedback", { exact: true })).toHaveCount(0);
      });
      await test.step("UC-LMS-012/013/014: faculty grades, releases and audits a correction", async () => {
        await selectDemoCourse(page, "lmsFaculty", "Grading");
        for (const [index, title] of titles.slice(0, 2).entries()) {
          await page.getByLabel("Assignment to grade").selectOption({ label: title });
          if (index === 1) {
            await page.getByLabel(/Points for submission/).fill("17");
            await page.getByLabel(/Feedback for submission/).fill("Faculty draft feedback");
            await page.getByRole("button", { name: "Save draft grade", exact: true }).click();
            await expect(page.getByText(/Grade DRAFT: 17/)).toBeVisible();
          }
          await page.getByRole("button", { name: /Release grade for submission/ }).click();
          await expect(page.getByText(/Grade RELEASED:/)).toBeVisible();
        }
        await page.getByLabel("Assignment to grade").selectOption({ label: titles[0] });
        await page.getByLabel(/Points for submission/).fill("18");
        await page.getByLabel(/Feedback for submission/).fill(correctedFeedback);
        await page.getByRole("button", { name: "Correct released grade", exact: true }).click();
        await expect(page.getByText(/Grade RELEASED: 18/)).toBeVisible();
        await student.page.reload();
        await chooseLoadedCourse(student.page, studentCourseId);
        await expect(student.page.getByText(correctedFeedback, { exact: true })).toBeVisible();
      });
      expect(problems).toEqual([]);
    } finally {
      await student.context.close(); await ta.context.close(); await observer.context.close();
    }
  });
});
