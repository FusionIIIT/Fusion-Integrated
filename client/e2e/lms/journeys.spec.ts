import { writeFileSync } from "node:fs";
import type { Browser, Page, Response } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName } from "../support/test";

import { localTime } from "./time";

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

interface JourneyContext {
  page: Page; student: { page: Page }; ta: { page: Page }; observer: { page: Page };
  note: string; section: string; news: string; correctedFeedback: string;
  titles: string[]; studentCourseId: number;
}
async function completeGradeLookup(page: Page) {
  await expect(page.getByRole("heading", { name: /^Submission \d+ · User/ }).first()).toBeVisible();
  const more = page.getByRole("button", { name: "Load more grades", exact: true });
  while (await more.isVisible()) {
    const response = page.waitForResponse((result) => result.url().includes("/grades/?cursor=") && result.request().method() === "GET");
    await more.click();
    expect((await response).status()).toBe(200);
    await expect.poll(async () => (await more.count()) === 0 || await more.isEnabled()).toBe(true);
  }
}

async function journey1(context: JourneyContext) {
  const { page } = context;
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
}

async function journey2(context: JourneyContext) {
  const { page, note, section } = context;
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
}

async function journey3(context: JourneyContext) {
  const { page, titles } = context;
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
}

async function journey4(context: JourneyContext) {
  const { ta, observer, news } = context;
  await selectDemoCourse(ta.page, "lmsTa", "My Courses");
  await ta.page.getByLabel("Announcement content").fill(news);
  await ta.page.getByRole("button", { name: "Post announcement", exact: true }).click();
  await expect(ta.page.getByText(news, { exact: true })).toBeVisible();
  await selectDemoCourse(observer.page, "lmsObserver", "My Courses");
  await expect(observer.page.getByText("Synthetic course syllabus for the browser journey", { exact: true })).toBeVisible();
  await expect(observer.page.getByText(news, { exact: true })).toBeVisible();
  await expect(observer.page.getByRole("region", { name: "Course assignments" })).toHaveCount(0);
  await expect(observer.page.getByRole("button", { name: "Post announcement" })).toHaveCount(0);
}

async function journey5(context: JourneyContext) {
  const { student, note, titles } = context;
  context.studentCourseId = await selectDemoCourse(student.page, "lmsStudent", "My Courses");
  await expect.poll(async () => {
    await student.page.reload();
    await chooseLoadedCourse(student.page, context.studentCourseId);
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
}

async function journey6(context: JourneyContext) {
  const { student, ta, titles } = context;
  await selectDemoCourse(ta.page, "lmsTa", "Grading");
  await ta.page.getByLabel("Assignment to grade").selectOption({ label: titles[0] });
  await completeGradeLookup(ta.page);
  await ta.page.getByLabel(/Points for submission/).fill("15");
  await ta.page.getByLabel(/Feedback for submission/).fill("Synthetic draft feedback");
  await ta.page.getByRole("button", { name: "Save draft grade", exact: true }).click();
  await expect(ta.page.getByText(/Grade DRAFT: 15/)).toBeVisible();
  await expect(ta.page.getByRole("button", { name: /Release grade/ })).toHaveCount(0);
  await student.page.reload();
  await chooseLoadedCourse(student.page, context.studentCourseId);
  await expect(student.page.getByText("Synthetic draft feedback", { exact: true })).toHaveCount(0);
}

async function journey7(context: JourneyContext) {
  const { page, student, correctedFeedback, titles } = context;
  await selectDemoCourse(page, "lmsFaculty", "Grading");
  for (const [index, title] of titles.slice(0, 2).entries()) {
    await page.getByLabel("Assignment to grade").selectOption({ label: title });
    await completeGradeLookup(page);
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
  await chooseLoadedCourse(student.page, context.studentCourseId);
  await expect(student.page.getByText(correctedFeedback, { exact: true })).toBeVisible();
}

interface JourneyRequest {
  useCases: number[]; actor: string; at: string; method: string; path: string; status: number;
}

async function recordJourney(useCases: number[], context: JourneyContext, records: JourneyRequest[], action: () => Promise<void>) {
  const actors = [
    { actor: "Faculty", page: context.page }, { actor: "Student", page: context.student.page },
    { actor: "TA", page: context.ta.page }, { actor: "Observer", page: context.observer.page },
  ];
  const listeners = actors.map(({ actor, page }) => {
    const listener = (response: Response) => {
      const url = new URL(response.url());
      if (url.pathname.startsWith("/api/v1/lms/")) records.push({ useCases, actor, at: new Date().toISOString(),
        method: response.request().method(), path: url.pathname + url.search, status: response.status() });
    };
    page.on("response", listener);
    return { page, listener };
  });
  try { await action(); }
  finally { for (const { page, listener } of listeners) page.off("response", listener); }
}


test.describe("lms: complete course journeys", () => {
  test.use(signedInAs("lmsFaculty"));
  test("accepts minute-boundary and second-precision datetime input", async ({ page }) => {
    await selectDemoCourse(page, "lmsFaculty", "Teaching");
    const base = new Date();
    base.setMilliseconds(0);
    for (const seconds of [0, 1, 59]) {
      base.setSeconds(seconds);
      const value = localTime(86_400, base.getTime());
      const field = page.getByLabel("Assignment due date (local time)");
      await field.fill(value);
      await expect(field).toHaveValue(value);
    }
  });
  test("UC-LMS-001 through UC-LMS-015: publication, submissions, grading and scheduled release", async ({ page, browser }) => {
    test.setTimeout(240_000);
    const problems: string[] = [];
    const records: JourneyRequest[] = [];
    const student = await anotherActor(browser, "lmsStudent", problems);
    const ta = await anotherActor(browser, "lmsTa", problems);
    const observer = await anotherActor(browser, "lmsObserver", problems);
    const note = uniqueName("Course note");
    const section = uniqueName("Course unit");
    const news = uniqueName("Course announcement");
    const correctedFeedback = uniqueName("Corrected released feedback");
    const titles = [uniqueName("Text exercise"), uniqueName("File exercise"), uniqueName("Link exercise")];
    const context: JourneyContext = { page, student, ta, observer, note, section, news, correctedFeedback, titles, studentCourseId: 0 };
    try {
      await test.step("UC-LMS-001/002: faculty configures course details", () => recordJourney([1, 2], context, records, () => journey1(context)));
      await test.step("UC-LMS-003/015: faculty organizes and schedules material", () => recordJourney([3, 15], context, records, () => journey2(context)));
      await test.step("UC-LMS-007/008: faculty creates and publishes all submission types", () => recordJourney([7, 8, 15], context, records, () => journey3(context)));
      await test.step("UC-LMS-004/005/006: TA and Observer read common content", () => recordJourney([4, 5, 6], context, records, () => journey4(context)));
      await test.step("UC-LMS-004/009/010/011/015: student downloads and submits released assignments", () => recordJourney([4, 9, 10, 11, 15], context, records, () => journey5(context)));
      await test.step("UC-LMS-012: TA grades a submission and cannot release it", () => recordJourney([12], context, records, () => journey6(context)));
      await test.step("UC-LMS-012/013/014: faculty grades, releases and audits a correction", () => recordJourney([12, 13, 14], context, records, () => journey7(context)));
      expect(problems).toEqual([]);
    } finally {
      const evidence = test.info().outputPath("lms-journey-requests.json");
      writeFileSync(evidence, JSON.stringify(records, null, 2));
      await test.info().attach("lms-journey-requests", {
        path: evidence, contentType: "application/json",
      });
      await student.context.close(); await ta.context.close(); await observer.context.close();
    }
  });
});
