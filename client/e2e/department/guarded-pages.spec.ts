import { expect, signedInAs, test } from "../support/test";

// Pages whose nav permission a student does not hold, opened directly.
const OFFICE_PAGES = ["inventory", "labs", "roles"];

test.describe("department: guarded pages", () => {
  test.use(signedInAs("deptStudent"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /department/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/department/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
