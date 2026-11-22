import { expect, signedInAs, test, uniqueName } from "../support/test";

test.describe("lms: course assignments", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/assignments", async ({ page }) => {
    await page.goto("/lms/assignments");
    await expect(page.getByRole("heading", { name: "Assignments", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /create assignment/i })).toHaveCount(0);
  });

  test("a student submits an assignment solution", async ({ page }) => {
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
