import { expect, signedInAs, test } from "../support/test";

test.describe("lms: course assignments", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/assignments", async ({ page }) => {
    await page.goto("/lms/assignments");
    await expect(page.getByRole("heading", { name: "Assignments", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: /create assignment/i })).toHaveCount(0);
  });
});
