import { expect, signedInAs, test, uniqueName } from "../support/test";

test.describe("lms: course assignments", () => {
  test.use(signedInAs("student"));

  test("a student views published assignments (UC-LMS-009)", async ({ page }) => {
    await page.goto("/lms/assignments");
    await expect(page.getByRole("heading", { name: "Assignments", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /create assignment/i })).toHaveCount(0);
    await expect(page.locator(".mantine-Card-root").first()).toBeVisible();
  });

  test("a student submits an assignment solution (UC-LMS-010)", async ({ page }) => {
    const solutionText = uniqueName("Solution implementation code");
    await page.goto("/lms/assignments");
    await expect(page.getByRole("heading", { name: "Assignments", level: 2 })).toBeVisible();

    const textCard = page.locator(".mantine-Card-root").filter({ hasText: "Format: TEXT" });
    const submitBtn = textCard.getByRole("button", { name: /submit work/i });
    await expect(submitBtn).toBeVisible();
    await submitBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/submission text/i).fill(solutionText);

    const submitted = page.waitForResponse((r) =>
      r.url().includes("/submissions") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Submit Work" }).click();
    expect((await submitted).status()).toBe(201);

    await expect(dialog).toBeHidden();
    await expect(page.getByText("Your submission has been recorded.")).toBeVisible();
  });
});

test.describe("lms: faculty assignment creation and publishing", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member creates a draft assignment and publishes it (UC-LMS-007, UC-LMS-008)", async ({ page }) => {
    const title = uniqueName("Homework Assignment");
    await page.goto("/lms/assignments");
    await expect(page.getByRole("heading", { name: "Assignments", level: 2 })).toBeVisible();

    const createBtn = page.getByRole("button", { name: /create assignment/i });
    await expect(createBtn).toBeVisible();
    await createBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/assignment title/i).fill(title);
    await dialog.getByLabel(/instructions/i).fill("Complete all theoretical exercises in chapter 2.");
    await dialog.getByLabel(/due date & time/i).fill("2028-12-31T23:59");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/lms/assignments") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Create Assignment" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    const card = page.locator(".mantine-Card-root").filter({ hasText: title });
    await expect(card).toBeVisible();
    await expect(card.getByText("DRAFT")).toBeVisible();

    const publishBtn = card.getByRole("button", { name: "Publish" });
    await expect(publishBtn).toBeVisible();

    const published = page.waitForResponse((r) =>
      r.url().includes("/publish/") && r.request().method() === "POST");
    await publishBtn.click();
    expect((await published).status()).toBe(200);

    await expect(card.getByText("PUBLISHED")).toBeVisible();
  });
});
