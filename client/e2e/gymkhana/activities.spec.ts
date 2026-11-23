import { expect, signedInAs, test, uniqueName } from "../support/test";
import {
  asAccount, choose, confirmedClub, find, freeSlot, manage, openPage, PDF, pick,
} from "./steps";
import { ACCOUNTS } from "../accounts";

// Each journey signs in two or three people, so it outlasts the default budget.
test.describe.configure({ timeout: 120_000 });

test.describe("gymkhana: a club head's work", () => {
  test.use(signedInAs("clubHead"));

  test("UC-GYM-002 and UC-GYM-003: a session is booked, and an event cannot take its slot", async ({ page, browser }) => {
    const club = await confirmedClub(browser);
    const slot = freeSlot();
    const title = uniqueName("E2E Session");
    await manage(page, club, "Bookings");

    await page.getByRole("button", { name: "Book session" }).click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: "Session title" }).fill(title);
    await choose(form, "Venue", "Hall 1");
    await form.getByLabel("Date").fill(slot.date);
    await form.getByLabel("Start time").fill(slot.start);
    await form.getByLabel("End time").fill(slot.end);
    await form.getByRole("button", { name: "Book", exact: true }).click();
    await expect(form).toBeHidden();
    await expect(page.getByRole("row").filter({ hasText: title })).toContainText("session");

    const event = uniqueName("E2E Event");
    await page.getByRole("button", { name: "Book event" }).click();
    await form.getByRole("textbox", { name: "Event name" }).fill(event);
    await pick(form, "Faculty Councillor", ACCOUNTS.facultyCouncillor.username);
    await choose(form, "Venue", "Hall 1");
    await form.getByLabel("Date").fill(slot.date);
    await form.getByLabel("Start time").fill("10:30");
    await form.getByLabel("End time").fill("11:30");
    await form.locator("input[type=file]").setInputFiles(PDF);
    await form.getByRole("button", { name: "Book", exact: true }).click();
    await expect(form.getByText(/already booked/)).toBeVisible();
    await form.getByLabel("Start time").fill("11:00");
    await form.getByRole("button", { name: "Book", exact: true }).click();
    await expect(form).toBeHidden();

    await openPage(page, "Events & Sessions", "Events & Sessions");
    await page.getByLabel("Date").fill(slot.date);
    await find(page, page.getByRole("row").filter({ hasText: event }));
    const saved = page.waitForEvent("download");
    await page.getByRole("button", { name: `Download poster for ${event}` }).click();
    expect((await saved).suggestedFilename()).toMatch(/^poster-.*\.pdf$/);
  });

  test("UC-GYM-006 and UC-GYM-007: a targeted student votes once", async ({ page, browser }) => {
    const club = await confirmedClub(browser);
    const title = uniqueName("E2E Poll");
    await manage(page, club, "Polls");
    await page.getByRole("button", { name: "Create poll" }).click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: "Title" }).fill(title);
    await form.getByLabel("Closes at").fill("2099-01-01T10:00");
    await form.getByRole("textbox", { name: "Choice 1" }).fill("Space");
    await form.getByRole("textbox", { name: "Choice 2" }).fill("Ocean");
    await choose(form, "Batch", "All batches");
    await choose(form, "Branch", "All branches");
    await form.getByRole("button", { name: "Add group" }).click();
    await form.getByRole("button", { name: "Create", exact: true }).click();
    await expect(form).toBeHidden();

    await asAccount(browser, "student", async (student) => {
      await openPage(student, "Voting Polls", "Voting Polls");
      const card = student.getByRole("region", { name: title });
      await find(student, card);
      await card.getByRole("radio", { name: "Ocean" }).check();
      await card.getByRole("button", { name: "Vote" }).click();
      await expect(card.getByText("Voted")).toBeVisible();
      await expect(card.getByRole("button", { name: "Vote" })).toHaveCount(0);
    });
  });

  test("UC-GYM-009: a budget request is kept open for tracking", async ({ page, browser }) => {
    const club = await confirmedClub(browser);
    const purpose = uniqueName("E2E Budget");
    await manage(page, club, "Budget requests");
    await page.getByRole("button", { name: "Request budget" }).click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: "Purpose" }).fill(purpose);
    await form.getByLabel("Amount").fill("500");
    await expect(form.getByRole("button", { name: "Submit request" })).toBeDisabled();
    await form.locator("input[type=file]").setInputFiles(PDF);
    await form.getByRole("button", { name: "Submit request" }).click();
    await expect(form).toBeHidden();
    await expect(page.getByRole("row").filter({ hasText: purpose })).toContainText("open");
  });

  test("UC-GYM-010 and UC-GYM-012: a report reaches the club's councillor", async ({ page, browser }) => {
    const club = await confirmedClub(browser);
    const event = uniqueName("E2E Report");
    await manage(page, club, "Event report");
    await page.getByRole("textbox", { name: "Event name" }).fill(event);
    await page.getByLabel("Event date and time").fill("2026-11-01T10:00");
    await pick(page, "Student incharge", ACCOUNTS.student.username);
    await page.locator("input[type=file]").setInputFiles(PDF);
    await page.getByRole("button", { name: "Submit report" }).click();
    await expect(page.getByText("Report submitted")).toBeVisible();

    await asAccount(browser, "facultyCouncillor", async (faculty) => {
      await openPage(faculty, "Club Reports", "Club Event Reports");
      const review = faculty.getByRole("button", { name: `Review ${event}` });
      await find(faculty, review);
      await review.click();
      const saved = faculty.waitForEvent("download");
      await faculty.getByRole("button", { name: "Download report" }).click();
      expect((await saved).suggestedFilename()).toMatch(/^report-.*\.pdf$/);
    });
  });

  test("a budget request can be opened and closed with the keyboard alone", async ({ page, browser }) => {
    const club = await confirmedClub(browser);
    await manage(page, club, "Budget requests");
    await page.getByRole("button", { name: "Request budget" }).focus();
    await page.keyboard.press("Enter");
    const form = page.getByRole("dialog");
    await expect(form).toBeVisible();
    for (const label of ["Purpose", "Amount (₹)"]) {
      await form.getByLabel(label).focus();
      await page.keyboard.type("7");
    }
    await page.keyboard.press("Tab");
    await expect(form.getByRole("button", { name: /supporting file/i })).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(form).toBeHidden();
  });
});
