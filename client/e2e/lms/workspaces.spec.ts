import { grantModuleWithoutCoursePermission } from "./iam-fixture";

import type { AccountKey } from "../accounts";
import { actAs, expect, openModuleNav, sidebar, signedInAs, test } from "../support/test";

for (const key of ["lmsFaculty", "lmsStudent", "lmsTa", "lmsObserver", "lmsPlain"] as AccountKey[]) {
  test.describe(`lms: ${key} workspace`, () => {
    test.use(signedInAs(key));
    test("opens My Courses through the real navigation", async ({ page }) => {
      await page.goto("/");
      await actAs(page, key);
      await openModuleNav(page, "Course Management");
      await sidebar(page).getByRole("link", { name: "My Courses", exact: true }).click();
      await expect(page.getByRole("heading", { name: "My Courses", exact: true })).toBeVisible();
      await expect(page.getByLabel("Course", { exact: true }).or(page.getByText(/No linked courses/))).toBeVisible();
    });
  });
}

for (const path of ["teaching", "grading"]) {
  test.describe(`lms: forbidden ${path}`, () => {
    test.use(signedInAs("lmsStudent"));
    test("refuses a student direct URL without mounting controls", async ({ page }) => {
      await page.goto("/");
      await actAs(page, "lmsStudent");
      await page.goto(`/lms/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  });
}

test.describe("lms: forbidden courses", () => {
  test.use(signedInAs("lmsNoCourse"));
  test("refuses a direct course URL without the course permission", async ({ page }) => {
    const restoreGrant = grantModuleWithoutCoursePermission();
    try {
      const sessionResponse = page.waitForResponse((response) => response.url().endsWith("/api/v1/me") && response.request().method() === "GET");
      await page.goto("/");
      const cached = await (await sessionResponse).json() as { csrf_token: string };
      const refreshed = await page.request.patch("/api/v1/me", {
        data: { active_role: "placement_officer" }, headers: { "X-CSRF-Token": cached.csrf_token },
      });
      expect(refreshed.ok()).toBe(true);
      const session = await refreshed.json() as { modules: string[]; permissions: string[] };
      expect(session.modules).toContain("lms");
      expect(session.permissions).not.toContain("lms.course.view");
      await actAs(page, "lmsNoCourse");
      await page.goto("/lms/courses");
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    } finally { restoreGrant(); }
  });
});
