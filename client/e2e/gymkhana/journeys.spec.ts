import { type Page } from "@playwright/test";

import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

// Needs `manage.py seed_gymkhana_venues --venue "LHTC 101"` on the dev database first.
const CLUB = uniqueName("E2E Club");
const DRIVE = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view";
const POLL = uniqueName("E2E Poll");
// A slot far enough ahead that reruns never collide with an earlier booking.
const DAY = new Date(Date.now() + (30 + Math.floor(Math.random() * 300)) * 86_400_000)
  .toISOString().slice(0, 10);
const now = new Date();
const TODAY = [now.getFullYear(), now.getMonth() + 1, now.getDate()]
  .map((n) => String(n).padStart(2, "0")).join("-");

test.describe.configure({ mode: "serial" });

async function open(page: Page, role: Parameters<typeof actAs>[1], link: string) {
  await page.goto("/");
  await actAs(page, role);
  await openModuleNav(page, "Gymkhana");
  await sidebar(page).getByRole("link", { name: link, exact: true }).click();
  await expect(page.getByRole("heading", { name: link, level: 2 })).toBeVisible();
}

async function pickPerson(page: Page, label: string, username: string) {
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("textbox", { name: label, exact: true }).fill(username);
  await page.getByRole("option", { name: new RegExp(username) }).click();
}

function posted(page: Page, path: string) {
  return page.waitForResponse((r) =>
    r.url().includes("/api/v1/gymkhana/") && r.url().endsWith(path)
    && r.request().method() === "POST");
}

test.describe("UC-GYM-001 and UC-GYM-011: Student Admin", () => {
  test.use(signedInAs("gymStudentAdmin"));

  test("creates a club and confirms it", async ({ page }) => {
    await open(page, "gymStudentAdmin", "Club Administration");
    await page.getByRole("button", { name: "Create club" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Name" }).fill(CLUB);
    await dialog.getByRole("textbox", { name: "Category" }).click();
    await page.getByRole("option", { name: "Technical" }).click();
    await dialog.getByRole("textbox", { name: "Description" }).fill("Built by the E2E suite.");
    await pickPerson(page, "Coordinator", "stu00002");
    await pickPerson(page, "Co-coordinator", "stu00003");
    await pickPerson(page, "Club Faculty Councillor", "fac00001");
    const created = posted(page, "clubs/create");
    await dialog.getByRole("button", { name: "Create club" }).click();
    expect((await created).status()).toBe(201);

    const row = page.getByRole("row").filter({ hasText: CLUB });
    await expect(row).toContainText("Open");
    const approved = posted(page, "approve");
    await row.getByRole("button", { name: `Confirm ${CLUB}` }).click();
    expect((await approved).status()).toBe(200);
    await expect(row).toContainText("Confirmed");
  });
});

test.describe("UC-GYM-004: a student applies", () => {
  test.use(signedInAs("gymApplicant"));

  test("applies to the confirmed club", async ({ page }) => {
    await open(page, "gymApplicant", "Clubs");
    await page.getByRole("button", { name: `Apply to ${CLUB}` }).click();
    await page.getByRole("dialog").getByRole("textbox", { name: /why you want to join/i })
      .fill("I build line followers.");
    const applied = posted(page, "memberships/apply");
    await page.getByRole("button", { name: "Send application" }).click();
    expect((await applied).status()).toBe(201);
    await expect(page.getByRole("row").filter({ hasText: CLUB })).toContainText("Open");
  });
});

test.describe("UC-GYM-005, 002, 003, 006, 009, 010: the Club Head", () => {
  test.use(signedInAs("gymCoordinator"));

  test("approves the application", async ({ page }) => {
    await open(page, "gymCoordinator", "My Clubs");
    await page.getByRole("button", { name: `Membership requests for ${CLUB}` }).click();
    await page.getByRole("checkbox", { name: /I build line followers/ }).check();
    const approved = posted(page, "memberships/approve");
    await page.getByRole("button", { name: "Approve selected" }).click();
    expect((await approved).status()).toBe(200);
    await expect(page.getByText("1 approved.")).toBeVisible();
  });

  test("books a session and an event, and an overlapping event is refused", async ({ page }) => {
    await open(page, "gymCoordinator", "Club Schedule");
    for (const [button, start, end, status] of [
      ["Book session", "10:00", "11:00", 201], ["Book event", "10:30", "12:00", 409],
      ["Book event", "12:00", "13:00", 201],
    ] as const) {
      await page.getByRole("button", { name: button }).click();
      const dialog = page.getByRole("dialog");
      await dialog.getByRole("textbox", { name: "Club" }).click();
      await page.getByRole("option", { name: CLUB }).click();
      if (button === "Book event") {
        await dialog.getByRole("textbox", { name: "Event name" }).fill("E2E Robo Race");
      }
      await dialog.getByRole("textbox", { name: "Venue" }).click();
      await page.getByRole("option", { name: "LHTC 101" }).click();
      await dialog.getByLabel("Date").fill(DAY);
      await dialog.getByLabel("Start time").fill(start);
      await dialog.getByLabel("End time").fill(end);
      await dialog.getByRole("textbox", { name: "Description" }).fill("E2E booking");
      if (button === "Book event") {
        await dialog.getByRole("textbox", { name: /poster/i }).fill(DRIVE);
      }
      const booked = posted(page, button === "Book event" ? "events" : "sessions");
      await dialog.getByRole("button", { name: "Book", exact: true }).click();
      expect((await booked).status()).toBe(status);
      if (status === 409) {
        await expect(dialog.getByText(/is already booked/)).toBeVisible();
        await dialog.getByRole("button", { name: "Cancel" }).click();
      }
    }
    await expect(page.getByRole("row").filter({ hasText: DAY })).toHaveCount(2);
    await expect(page.getByRole("row").filter({ hasText: DAY })
      .filter({ hasText: "E2E Robo Race" })).toHaveCount(1);
  });

  test("creates a poll for 2021 CSE", async ({ page }) => {
    await open(page, "gymCoordinator", "My Clubs");
    await page.getByRole("button", { name: `New poll for ${CLUB}` }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Title" }).fill(POLL);
    await dialog.getByRole("textbox", { name: "Description" }).fill("Pick a workshop.");
    await dialog.getByLabel(/open until/i).fill(DAY);
    await dialog.getByRole("textbox", { name: "Choice 1" }).fill("Drones");
    await dialog.getByRole("textbox", { name: "Choice 2" }).fill("ROS");
    await dialog.getByRole("textbox", { name: "Batch 1" }).fill("2021");
    await dialog.getByRole("textbox", { name: /branch/i }).fill("CSE");
    const created = posted(page, "polls/create");
    await dialog.getByRole("button", { name: "Create poll" }).click();
    expect((await created).status()).toBe(201);
  });

  test("submits a budget request and an event report", async ({ page }) => {
    await open(page, "gymCoordinator", "My Clubs");
    await page.getByRole("button", { name: `Request budget for ${CLUB}` }).click();
    let dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Purpose" }).fill("Motors");
    await dialog.getByRole("textbox", { name: /amount/i }).fill("4500");
    await dialog.getByRole("textbox", { name: "Description" }).fill("Four motors.");
    await dialog.getByRole("textbox", { name: /supporting document/i }).fill(DRIVE);
    const budget = posted(page, "budget-requests/create");
    await dialog.getByRole("button", { name: "Submit request" }).click();
    expect((await budget).status()).toBe(201);

    await page.getByRole("button", { name: `Submit event report for ${CLUB}` }).click();
    dialog = page.getByRole("dialog");
    await pickPerson(page, "Student in charge", "stu00003");
    await dialog.getByRole("textbox", { name: "Event name" }).fill("E2E Robo Race");
    // The club was created today, and a report may not predate its club.
    await dialog.getByLabel("Held on").fill(`${TODAY}T00:00`);
    await dialog.getByRole("textbox", { name: "Description" }).fill("It went well.");
    await dialog.getByRole("textbox", { name: /report file/i }).fill(DRIVE);
    const report = posted(page, "event-reports/create");
    await dialog.getByRole("button", { name: "Submit report" }).click();
    expect((await report).status()).toBe(201);
  });
});

test.describe("UC-GYM-007: a targeted student votes once", () => {
  test.use(signedInAs("gymApplicant"));

  test("votes and sees the vote recorded", async ({ page }) => {
    await open(page, "gymApplicant", "Polls");
    const card = page.getByRole("article", { name: POLL });
    await card.getByRole("radio", { name: "ROS" }).check();
    const voted = posted(page, "votes");
    await card.getByRole("button", { name: "Vote" }).click();
    expect((await voted).status()).toBe(201);
    await expect(card.getByText("You voted for")).toBeVisible();
  });
});

test.describe("UC-GYM-012: the assigned councillor reviews", () => {
  test.use(signedInAs("gymCouncillor"));

  test("opens the club's report", async ({ page }) => {
    await open(page, "gymCouncillor", "Club Reports");
    const row = page.getByRole("row").filter({ hasText: CLUB });
    await row.getByRole("button", { name: /review/i }).first().click();
    await expect(page.getByRole("link", { name: "Open the report file" }))
      .toHaveAttribute("href", DRIVE);
  });
});

test.describe("UC-GYM-008: the Club Head hands over", () => {
  test.use(signedInAs("gymCoordinator"));

  test("replaces both leaders and stops leading the club", async ({ page }) => {
    await open(page, "gymCoordinator", "My Clubs");
    await page.getByRole("button", { name: `Change leadership for ${CLUB}` }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "New coordinator", exact: true }).fill("");
    await pickPerson(page, "New coordinator", "stu00004");
    await dialog.getByRole("textbox", { name: "New co-coordinator", exact: true }).fill("");
    await pickPerson(page, "New co-coordinator", "stu00003");
    const changed = posted(page, "leadership");
    await dialog.getByRole("button", { name: "Change leadership" }).click();
    expect((await changed).status()).toBe(200);
    await expect(page.getByRole("button", { name: `New poll for ${CLUB}` })).toHaveCount(0);
  });
});
