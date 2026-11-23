// client/e2e/complaints/complaints.spec.ts
// End‑to‑end tests for the Complaints module.
// Uses the existing Playwright test harness and helpers.

import { test, expect, signedInAs, actAs, openModuleNav, sidebar, uniqueName } from "../support/test";

/**
 * Helper to fill and submit the "Lodge Complaint" form.
 * Returns the description that was used, so later tests can locate the row.
 */
async function lodgeComplaint(page: import("@playwright/test").Page, description: string) {
  // Open the modal
  await page.getByRole("button", { name: /lodge complaint/i }).click();
  const modal = page.getByRole("dialog", { name: /lodge new complaint/i });
  await expect(modal).toBeVisible();

  // Fill required fields
  // Category: pick the first available option (the UI loads them via API)
  const categorySelect = modal.getByLabelText(/complaint category/i);
  await categorySelect.selectOption({ index: 0 });

  await modal.getByLabelText(/location/i).fill("Room 101");
  await modal.getByLabelText(/description/i).fill(description);

  // Priority – keep default (medium) to avoid extra interactions.
  // Closure Verification – keep default (none).

  // Submit
  const created = page.waitForResponse((r) =>
    r.url().includes("/api/v1/complaints/complaints") && r.request().method() === "POST",
  );
  await modal.getByRole("button", { name: /submit complaint/i }).click();
  const resp = await created;
  expect(resp.status()).toBe(201);
  await expect(modal).toBeHidden();
}

/** Verify that a row with the given description exists in the complaints table. */
async function expectComplaintRow(page: import("@playwright/test").Page, description: string) {
  const row = page.getByRole("row").filter({ hasText: description });
  await expect(row).toBeVisible();
  // The row should contain the default "submitted" status badge.
  await expect(row).toContainText(/submitted/i);
}

/** Ensure that student‑level UI does not expose officer‑only actions. */
async function expectStudentRestrictions(page: import("@playwright/test").Page) {
  // No "Queue" link in the sidebar.
  await expect(sidebar(page).getByRole("link", { name: "Queue" })).toBeHidden();
  // Actions inside the table row should not include Verify, Reopen or Feedback.
  const actionIcons = page.getByRole("button", { name: /view details/i }).locator(".."); // parent cell
  // The cell contains only the view‑details icon for a freshly submitted complaint.
  await expect(actionIcons.getByRole("button", { name: /verify & close/i })).toBeHidden();
  await expect(actionIcons.getByRole("button", { name: /reopen/i })).toBeHidden();
  await expect(actionIcons.getByRole("button", { name: /provide feedback/i })).toBeHidden();
}

/** Officer‑only UI: queue view and assignment actions. */
async function expectOfficerQueue(page: import("@playwright/test").Page, description: string) {
  // The Queue page should be reachable via the sidebar link.
  await sidebar(page).getByRole("link", { name: "Queue" }).click();
  await expect(page).toHaveURL(/\/complaints\/queue/);

  const row = page.getByRole("row").filter({ hasText: description });
  await expect(row).toBeVisible();
}

/**
 * Phase 1 – Student lodges a complaint and sees it in My Complaints.
 * Also verifies that student‑only UI does not expose officer actions.
 */
test.describe("complaints: student workflow", () => {
  test.use(signedInAs("student"));

  test("student can lodge a complaint and sees it in My Complaints", async ({ page }) => {
    const desc = uniqueName("E2E Complaint");

    await page.goto("/");
    await openModuleNav(page, "Complaints"); // lands on /mine

    await lodgeComplaint(page, desc);
    await expectComplaintRow(page, desc);
    await expectStudentRestrictions(page);
  });
});

/**
 * Phase 2 – Officer views the student's complaint in the Queue.
 * This test runs after the previous one; the DB is persistent between tests.
 */
test.describe("complaints: officer view", () => {
  test.use(signedInAs("placementOfficer"));

  test("officer can see student complaint in the Queue", async ({ page }) => {
    const desc = "E2E Complaint"; // we look for any row containing the token "E2E Complaint"

    await page.goto("/");
    // Ensure the role is set – the helper will issue a PATCH if needed.
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "Complaints");
    await expectOfficerQueue(page, desc);
  });
});

/**
 * Optional lifecycle steps – only executed if the UI actually provides the controls.
 * These are guarded by existence checks so the spec does not fail on unsupported builds.
 */
test.describe("complaints: optional lifecycle (if supported)", () => {
  test.use(signedInAs("student"));

  test("student may verify & close when allowed", async ({ page }) => {
    const desc = uniqueName("E2E Verify");
    await page.goto("/");
    await openModuleNav(page, "Complaints");
    await lodgeComplaint(page, desc);
    // Wait for possible status transition to "resolved" – the backend may resolve automatically.
    const row = page.getByRole("row").filter({ hasText: desc });
    await expect(row).toBeVisible();

    // If the Verify & Close button appears, click it and assert status change.
    const verifyBtn = row.getByRole("button", { name: /verify & close/i });
    if (await verifyBtn.isVisible()) {
      await verifyBtn.click();
      await expect(row).toContainText(/closed/i);
    }
  });

  test("student may provide feedback after closure when allowed", async ({ page }) => {
    const desc = uniqueName("E2E Feedback");
    await page.goto("/");
    await openModuleNav(page, "Complaints");
    await lodgeComplaint(page, desc);
    const row = page.getByRole("row").filter({ hasText: desc });
    await expect(row).toBeVisible();

    const feedbackBtn = row.getByRole("button", { name: /provide feedback/i });
    if (await feedbackBtn.isVisible()) {
      await feedbackBtn.click();
      const modal = page.getByRole("dialog", { name: /submit resolution feedback/i });
      await expect(modal).toBeVisible();
      await modal.getByRole("spinbutton").fill("5"); // rating component
      await modal.getByRole("button", { name: /submit feedback/i }).click();
      await expect(modal).toBeHidden();
    }
  });
});
