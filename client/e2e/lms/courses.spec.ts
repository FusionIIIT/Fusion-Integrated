import { expect, signedInAs, test } from "../support/test";

test.describe("lms: courses and authorization guards", () => {
  test.use(signedInAs("student"));

  test("a student who opens /lms/grading is told it is not for them", async ({ page }) => {
    await page.goto("/lms/grading");
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
  });

  test("a student can navigate to /lms/courses", async ({ page }) => {
    await page.goto("/lms/courses");
    await expect(page.getByRole("heading", { name: "Courses & Workspaces" })).toBeVisible();
  });
});
