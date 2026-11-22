import { expect, signedInAs, test, uniqueName } from "../support/test";

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

test.describe("lms: faculty course management", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member can edit course syllabus and schedule", async ({ page }) => {
    const updatedSyllabus = uniqueName("Syllabus");
    await page.goto("/lms/courses");
    await expect(page.getByRole("heading", { name: "Courses & Workspaces" })).toBeVisible();

    const editBtn = page.getByRole("button", { name: /edit course details/i });
    await expect(editBtn).toBeVisible();
    await editBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/syllabus/i).fill(updatedSyllabus);

    const saved = page.waitForResponse((r) =>
      r.url().includes("/api/v1/lms/courses/") && r.request().method() === "PATCH");
    await dialog.getByRole("button", { name: "Save Changes" }).click();
    expect((await saved).status()).toBe(200);

    await expect(dialog).toBeHidden();
    await expect(page.getByText(updatedSyllabus)).toBeVisible();
  });
});
