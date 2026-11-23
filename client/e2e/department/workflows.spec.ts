import type { BrowserContext, Page } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName } from "../support/test";

test("Department staff and student complete the implemented workflows", async ({ browser }) => {
  const contexts: BrowserContext[] = [];
  const errors: string[] = [];
  async function actor(key: AccountKey): Promise<Page> {
    const context = await browser.newContext(signedInAs(key));
    contexts.push(context);
    const page = await context.newPage();
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.url().includes("/api/") && response.status() >= 500) {
        errors.push(`${response.status()} ${response.url()}`);
      }
    });
    await page.goto("/");
    await actAs(page, key);
    return page;
  }

  const admin = await actor("departmentAdmin");
  const faculty = await actor("departmentFaculty");
  const hod = await actor("departmentHead");
  const student = await actor("student");
  try {
    await announcementJourney(faculty, student, hod);
    await stockJourney(admin, faculty, hod);
    await feedbackJourney(student, admin, hod);
    await labJourney(admin, faculty);
    await detailsJourney(admin, hod);
    const identity = await faculty.request.get("/api/v1/me");
    expect(identity.ok()).toBe(true);
    await timetableJourney(admin, student, (await identity.json()).user.id);
    expect(errors).toEqual([]);
  } finally {
    for (const context of contexts) await context.close();
  }
});

async function navigate(page: Page, link: string) {
  await openModuleNav(page, "Department");
  await sidebar(page).getByRole("link", { name: link, exact: true }).click();
}

// UC-DEPT-002, UC-DEPT-001, UC-DEPT-003: publish, read, maintain.
async function announcementJourney(faculty: Page, student: Page, hod: Page) {
  const announcement = uniqueName("Department seminar");
  await navigate(faculty, "Announcements");
  await faculty.getByRole("button", { name: "New announcement" }).click();
  await faculty.getByRole("textbox", { name: "Announcement", exact: true }).fill(announcement);
  await faculty.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(faculty.getByText(announcement, { exact: true })).toBeVisible();
  await navigate(student, "Announcements");
  await expect(student.getByText(announcement, { exact: true })).toBeVisible();
  await navigate(hod, "Announcements");
  const managed = hod.getByRole("article").filter({ hasText: announcement }).filter({ has: hod.getByRole("button", { name: "Hide" }) });
  await managed.getByRole("button", { name: "Hide" }).click();
  await expect(managed).toHaveCount(0);
  await student.reload();
  await expect(student.getByText(announcement, { exact: true })).toHaveCount(0);
}

// UC-DEPT-004, UC-DEPT-005, UC-DEPT-006, UC-DEPT-019: insert, request, approve, issue.
async function stockJourney(admin: Page, faculty: Page, hod: Page) {
  const item = uniqueName("Cable");
  await navigate(admin, "Inventory");
  await admin.getByLabel("Item name", { exact: false }).fill(item);
  await admin.getByRole("button", { name: "Add stock" }).click();
  await expect(admin.getByText(item, { exact: true })).toBeVisible();
  await navigate(faculty, "Inventory");
  await faculty.getByRole("button", { name: `Request ${item}`, exact: true }).click();
  await faculty.getByRole("button", { name: "Submit request" }).click();
  await expect(faculty.getByText("Saved.", { exact: true })).toBeVisible();
  await navigate(hod, "Stock requests");
  const pending = hod.getByRole("article").filter({ hasText: item });
  await pending.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(pending).toHaveCount(0);
  await navigate(admin, "Stock requests");
  const approved = admin.getByRole("article").filter({ hasText: item });
  await approved.getByRole("button", { name: "Issue stock" }).click();
  await expect(approved).toHaveCount(0);
  await navigate(faculty, "Stock requests");
  await expect(faculty.getByText(`${item} · 1 · issued`, { exact: true })).toBeVisible();
}

// UC-DEPT-007, UC-DEPT-008, UC-DEPT-014: confidential submission, review, disposition.
async function feedbackJourney(student: Page, admin: Page, hod: Page) {
  const feedback = uniqueName("Repair laboratory ramp");
  await navigate(student, "Submit feedback");
  await student.getByRole("textbox", { name: "Feedback" }).fill(feedback);
  await student.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(student.getByText("Feedback submitted.")).toBeVisible();
  await navigate(hod, "Feedback inbox");
  await expect(hod.getByText(feedback, { exact: true })).toHaveCount(0);
  await navigate(admin, "Feedback inbox");
  const review = admin.getByRole("article").filter({ hasText: feedback });
  await review.getByLabel("Category", { exact: false }).fill("Access");
  await review.getByRole("button", { name: "Record review" }).click();
  await expect(review.getByRole("button", { name: "Resolve" })).toBeVisible();
  await hod.reload();
  const disposition = hod.getByRole("article").filter({ hasText: feedback });
  await disposition.getByLabel("HOD oversight notes").fill("Discuss at the next meeting");
  await disposition.getByRole("button", { name: "Record oversight" }).click();
  await expect(disposition.getByText(/HOD oversight recorded/)).toBeVisible();
  await expect(disposition.getByText(/reviewed/)).toBeVisible();
  await disposition.getByRole("button", { name: "Resolve" }).click();
  await expect(disposition.getByText(/resolved/)).toBeVisible();
}

// UC-DEPT-011, UC-DEPT-017: maintain and read a scoped lab profile.
async function labJourney(admin: Page, faculty: Page) {
  const lab = uniqueName("Teaching lab");
  await navigate(admin, "Lab resources");
  await admin.getByLabel("Lab name", { exact: false }).fill(lab);
  await admin.getByLabel("Equipment and resource details", { exact: false }).fill("Ten workstations");
  await admin.getByRole("button", { name: "Save lab profile" }).click();
  await expect(admin.getByText(lab, { exact: true })).toBeVisible();
  await navigate(faculty, "Lab resources");
  await expect(faculty.getByRole("article").filter({ hasText: lab })).toContainText("Ten workstations");
}

// UC-DEPT-010, UC-DEPT-012: publish general details; official changes need approval.
async function detailsJourney(admin: Page, hod: Page) {
  const official = uniqueName("Mechanical Engineering");
  await navigate(admin, "Department details");
  await admin.getByLabel("General information").fill("Office opens at nine");
  await admin.getByRole("button", { name: "Save general information" }).click();
  await expect(admin.getByText("General information saved.")).toBeVisible();
  await admin.getByLabel("Proposed value", { exact: false }).fill(official);
  await admin.getByRole("button", { name: "Submit for approval" }).click();
  await expect(admin.getByText(official, { exact: true })).toBeVisible();
  await navigate(hod, "Department details");
  const proposal = hod.getByRole("article").filter({ hasText: official })
    .filter({ hasText: "Official name ·" });
  await proposal.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(proposal.getByText("Official name · approved", { exact: true })).toBeVisible();
  await admin.reload();
  await expect(admin.getByText(official, { exact: true })).toHaveCount(2);
}

// UC-DEPT-009, UC-DEPT-018: publish a slot and read it in the student's cohort.
async function timetableJourney(admin: Page, student: Page, instructorId: number) {
  const course = uniqueName("Workshop");
  await navigate(admin, "Academic timetable");
  await admin.getByRole("button", { name: "Add timetable slot" }).click();
  await admin.getByLabel("Class or lab title", { exact: false }).fill(course);
  await admin.getByRole("textbox", { name: "Term", exact: true }).fill(uniqueName("Autumn"));
  await admin.getByLabel("Programme", { exact: false }).fill("B.Tech");
  await admin.getByLabel("Room", { exact: false }).fill("Lab 1");
  await admin.getByLabel("Start time", { exact: false }).fill("10:00");
  await admin.getByLabel("End time", { exact: false }).fill("11:00");
  await admin.getByLabel("Batch year", { exact: false }).fill("2024");
  await admin.getByLabel("Instructor ID", { exact: false }).fill(String(instructorId));
  await admin.getByRole("button", { name: "Save timetable slot" }).click();
  await expect(admin.getByText(course, { exact: true })).toBeVisible();
  await navigate(student, "Academic timetable");
  await expect(student.getByText(course, { exact: true })).toBeVisible();
}
