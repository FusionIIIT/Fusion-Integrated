import { expect, signedInAs, test } from "../support/test";

// BADMS restricted operator/admin pages opened directly by an unauthorized role (e.g. student).
const RESTRICTED_BADMS_PAGES = [
  "backups",
  "schedules",
  "security-policies",
  "reports",
  "audit-logs",
];

test.describe("badms: restricted pages access control", () => {
  test.use(signedInAs("student"));

  for (const path of RESTRICTED_BADMS_PAGES) {
    test(`a student navigating to /badms/${path} is refused by route guard`, async ({ page }) => {
      await page.goto(`/badms/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
