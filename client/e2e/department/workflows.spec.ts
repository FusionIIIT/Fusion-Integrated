import type { BrowserContext, Page } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, expect, signedInAs, test, uniqueName } from "../support/test";

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
    if (key === "departmentHead" || key === "departmentAdmin") await actAs(page, key);
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
    await timetableJourney(admin, student);
    expect(errors).toEqual([]);
  } finally {
    for (const context of contexts) await context.close();
  }
});

// UC-DEPT-002, UC-DEPT-001, UC-DEPT-003: publish, read, maintain.
async function announcementJourney(faculty: Page, student: Page, hod: Page) {
  const announcement = uniqueName("Department seminar");
  await faculty.goto("/department/announcements");
  await faculty.getByRole("button", { name: "New announcement" }).click();
  await faculty.getByRole("textbox", { name: "Announcement", exact: true }).fill(announcement);
  await faculty.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(faculty.getByText(announcement, { exact: true })).toBeVisible();
  await student.goto("/department/announcements");
  await expect(student.getByText(announcement, { exact: true })).toBeVisible();
  await hod.goto("/department/announcements");
  const managed = hod.locator(".mantine-Paper-root").filter({ hasText: announcement }).filter({ has: hod.getByRole("button", { name: "Hide" }) });
  await managed.getByRole("button", { name: "Hide" }).click();
  await expect(managed).toHaveCount(0);
  await student.reload();
  await expect(student.getByText(announcement, { exact: true })).toHaveCount(0);
}

// UC-DEPT-004, UC-DEPT-005, UC-DEPT-006, UC-DEPT-019: insert, request, approve, issue.
async function stockJourney(admin: Page, faculty: Page, hod: Page) {
  const item = uniqueName("Cable");
  await admin.goto("/department/inventory");
  await admin.getByLabel("Item name", { exact: false }).fill(item);
  await admin.getByRole("button", { name: "Add stock" }).click();
  await expect(admin.getByText(item, { exact: true })).toBeVisible();
  await faculty.goto("/department/inventory");
  await faculty.getByRole("button", { name: `Request ${item}`, exact: true }).click();
  await faculty.getByRole("button", { name: "Submit request" }).click();
  await expect(faculty.getByText("Saved.", { exact: true })).toBeVisible();
  await hod.goto("/department/stock-requests");
  const pending = hod.locator(".mantine-Paper-root").filter({ hasText: item });
  await pending.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(pending).toHaveCount(0);
  await admin.goto("/department/stock-requests");
  const approved = admin.locator(".mantine-Paper-root").filter({ hasText: item });
  await approved.getByRole("button", { name: "Issue stock" }).click();
  await expect(approved).toHaveCount(0);
  await faculty.goto("/department/stock-requests");
  await expect(faculty.getByText(`${item} · 1 · issued`, { exact: true })).toBeVisible();
}

// UC-DEPT-007, UC-DEPT-008, UC-DEPT-014: confidential submission, review, disposition.
async function feedbackJourney(student: Page, admin: Page, hod: Page) {
  const feedback = uniqueName("Repair laboratory ramp");
  await student.goto("/department/feedback");
  await student.getByRole("textbox", { name: "Feedback" }).fill(feedback);
  await student.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(student.getByText("Feedback submitted.")).toBeVisible();
  await hod.goto("/department/feedback-inbox");
  await expect(hod.getByText(feedback, { exact: true })).toHaveCount(0);
  await admin.goto("/department/feedback-inbox");
  const review = admin.locator(".mantine-Paper-root").filter({ hasText: feedback });
  await review.getByLabel("Category", { exact: false }).fill("Access");
  await review.getByRole("button", { name: "Record review" }).click();
  await expect(review.getByRole("button", { name: "Resolve" })).toBeVisible();
  await hod.reload();
  const disposition = hod.locator(".mantine-Paper-root").filter({ hasText: feedback });
  await disposition.getByRole("button", { name: "Resolve" }).click();
  await expect(disposition.getByText(/resolved/)).toBeVisible();
}

// UC-DEPT-011, UC-DEPT-017: maintain and read a scoped lab profile.
async function labJourney(admin: Page, faculty: Page) {
  const lab = uniqueName("Teaching lab");
  await admin.goto("/department/labs");
  await admin.getByLabel("Lab name", { exact: false }).fill(lab);
  await admin.getByLabel("Equipment and resource details", { exact: false }).fill("Ten workstations");
  await admin.getByRole("button", { name: "Save lab profile" }).click();
  await expect(admin.getByText(lab, { exact: true })).toBeVisible();
  await faculty.goto("/department/labs");
  await expect(faculty.locator(".mantine-Paper-root").filter({ hasText: lab })).toContainText("Ten workstations");
}

// UC-DEPT-010, UC-DEPT-012: publish general details; official changes need approval.
async function detailsJourney(admin: Page, hod: Page) {
  const official = uniqueName("Mechanical Engineering");
  await admin.goto("/department/details");
  await admin.getByLabel("General information").fill("Office opens at nine");
  await admin.getByRole("button", { name: "Save general information" }).click();
  await expect(admin.getByText("General information saved.")).toBeVisible();
  await admin.getByLabel("Proposed value", { exact: false }).fill(official);
  await admin.getByRole("button", { name: "Submit for approval" }).click();
  await expect(admin.getByText(official, { exact: true })).toBeVisible();
  await hod.goto("/department/details");
  const proposal = hod.locator(".mantine-Paper-root").filter({ hasText: official })
    .filter({ hasText: "Official name ·" });
  await proposal.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(proposal.getByText("Official name · approved", { exact: true })).toBeVisible();
  await admin.reload();
  await expect(admin.getByText(official, { exact: true })).toHaveCount(2);
}

// UC-DEPT-009, UC-DEPT-018: publish a slot and read it in the student's cohort.
async function timetableJourney(admin: Page, student: Page) {
  const course = uniqueName("Workshop");
  await admin.goto("/department/timetable");
  await admin.getByRole("button", { name: "Add timetable slot" }).click();
  await admin.getByLabel("Class or lab title", { exact: false }).fill(course);
  await admin.getByRole("textbox", { name: "Term", exact: true }).fill(uniqueName("Autumn"));
  await admin.getByLabel("Programme", { exact: false }).fill("B.Tech");
  await admin.getByLabel("Room", { exact: false }).fill("Lab 1");
  await admin.getByLabel("Start time", { exact: false }).fill("10:00");
  await admin.getByLabel("End time", { exact: false }).fill("11:00");
  await admin.getByLabel("Batch year", { exact: false }).fill("2024");
  await admin.getByLabel("Instructor ID", { exact: false }).fill("1");
  await admin.getByRole("button", { name: "Save timetable slot" }).click();
  await expect(admin.getByText(course, { exact: true })).toBeVisible();
  await student.goto("/department/timetable");
  await expect(student.getByText(course, { exact: true })).toBeVisible();
}
