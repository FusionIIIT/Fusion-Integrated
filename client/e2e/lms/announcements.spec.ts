import { expect, signedInAs, test } from "../support/test";

test.describe("lms: course announcements", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/announcements", async ({ page }) => {
    await page.goto("/lms/announcements");
    await expect(page.getByRole("heading", { name: "Announcements" })).toBeVisible();
    await expect(page.getByRole("button", { name: /new announcement/i })).toHaveCount(0);
  });
});
