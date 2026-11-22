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
