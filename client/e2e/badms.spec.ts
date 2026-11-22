import { expect, test } from "@playwright/test";

const session = {
  user: { id: 4101, username: "student", display_name: "Test Student",
    kind: "student", email: "student@example.test" },
  active_role: "student",
  roles: ["student"],
  permissions: ["badms.backup.view", "badms.archive.create", "badms.archive.view_self"],
  modules: ["badms"],
  navigation: [],
  csrf_token: "test-csrf",
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/me", (route) => route.fulfill({ json: session }));
  await page.route("**/api/v1/badms/backup_runs**", (route) => route.fulfill({
    json: { next: null, previous: null, results: [{ id: 8, trigger: "scheduled",
      status: "success", dataset: "student_records", started_at: "2026-11-22T08:00:00Z",
      completed_at: "2026-11-22T08:01:00Z", checksum_sha256: "a".repeat(64),
      integrity_verified: true, outcome: "Verified" }] },
  }));
  await page.route("**/api/v1/badms/archive_requests**", (route) => route.fulfill({
    json: { next: null, previous: null, results: [{ id: 12, user_id: 4101,
      department: "CSE", file_name: "thesis-dataset.zip", file_date: "2026-11-20",
      owners: ["Test Student"], file_type: "application/zip", reason: "Research retention",
      initial_classification: "Routine", classification: "", status: "Submitted",
      decision_note: "", checksum_sha256: "b".repeat(64), created_at: "2026-11-22T08:00:00Z",
      updated_at: "2026-11-22T08:00:00Z" }] },
  }));
});

test("student can view backup status and their archive request", async ({ page }) => {
  await page.goto("/badms");
  await expect(page.getByRole("heading", { name: "Backup and Archive Management" })).toBeVisible();
  await expect(page.getByText("Run #8 · student_records")).toBeVisible();
  await page.getByRole("link", { name: "Open archives" }).click();
  await expect(page.getByRole("heading", { name: "Secure archives" })).toBeVisible();
  await expect(page.getByText("thesis-dataset.zip")).toBeVisible();
  await expect(page.getByText("Submitted", { exact: true })).toBeVisible();
});
