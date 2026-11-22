import { expect, signedInAs, test } from "../support/test";

test.describe("lms: course materials", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/materials", async ({ page }) => {
    await page.goto("/lms/materials");
    await expect(page.getByRole("heading", { name: "Course Materials" })).toBeVisible();
    await expect(page.getByRole("button", { name: /add material/i })).toHaveCount(0);
  });
});
