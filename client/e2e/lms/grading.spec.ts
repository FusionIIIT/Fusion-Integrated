import { expect, signedInAs, test, uniqueName } from "../support/test";

test.describe("lms: grading management and release", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member grades a submission and releases grades (UC-LMS-012, UC-LMS-013)", async ({ page }) => {
    const feedback = uniqueName("Comprehensive grading review remarks");
    await page.goto("/lms/grading");
    await expect(page.getByRole("heading", { name: "Submissions & Grading" })).toBeVisible();

    const gradeBtn = page.getByRole("table").getByRole("button", { name: "Grade", exact: true }).first();
    await expect(gradeBtn).toBeVisible();
    await gradeBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/points awarded/i).fill("92.50");
    await dialog.getByLabel(/feedback/i).fill(feedback);

    const saved = page.waitForResponse((r) =>
      r.url().includes("/grade/") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save Draft Grade" }).click();
    expect([200, 201]).toContain((await saved).status());

    await expect(dialog).toBeHidden();

    // Release grades to students (UC-LMS-013)
    page.on("dialog", (d) => d.accept());
    const publishBtn = page.getByRole("button", { name: "Publish Draft Grades" });
    await expect(publishBtn).toBeVisible();

    const published = page.waitForResponse((r) =>
      r.url().includes("/publish-grades/") && r.request().method() === "POST");
    await publishBtn.click();
    expect((await published).status()).toBe(200);

    await expect(page.getByText(/published grades/i)).toBeVisible();
  });
});

test.describe("lms: student grade viewing", () => {
  test.use(signedInAs("student"));

  test("a student views grades and feedback on /lms/grades (UC-LMS-014)", async ({ page }) => {
    await page.goto("/lms/grades");
    await expect(page.getByRole("heading", { name: "My Grades & Submissions" })).toBeVisible();

    const card = page.locator(".mantine-Card-root").first();
    await expect(card).toBeVisible();
    await expect(card.getByText("Max:", { exact: false })).toBeVisible();
  });
});
