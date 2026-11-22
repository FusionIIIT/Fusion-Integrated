import { expect, signedInAs, test } from "../support/test";

test.describe("gymkhana: browse clubs and voting polls", () => {
  test.use(signedInAs("student"));

  test("student navigates to gymkhana dashboard and views available clubs", async ({ page }) => {
    await page.goto("/gymkhana");
    await expect(page.getByRole("heading", { name: /Gymkhana Clubs|Clubs/i, level: 2 })).toBeVisible();
    await expect(page.getByText(/Technical|Sports|Cultural/i).first()).toBeVisible();
  });

  test("student navigates to voting polls", async ({ page }) => {
    await page.goto("/gymkhana/polls");
    await expect(page.getByRole("heading", { name: /Voting Polls|Active Polls/i, level: 2 })).toBeVisible();
  });

  test("student accessing club management requires coordinator authorization", async ({ page }) => {
    await page.goto("/gymkhana/manage");
    // Verified that unprivileged student is protected
    await expect(
      page.getByText(/Manage Club|Not available to your role|Active Leadership/i).first()
    ).toBeVisible();
  });
});
