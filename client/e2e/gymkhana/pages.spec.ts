import { expect, signedInAs, test } from "../support/test";

// Restricted pages for roles other than the allowed ones
const ADMIN_PAGES = ["admin", "reports"];

test.describe("gymkhana: student pages and route guards", () => {
  test.use(signedInAs("student"));

  test("a student can view gymkhana clubs page", async ({ page }) => {
    await page.goto("/gymkhana/clubs");
    await expect(page.getByText("Gymkhana Clubs")).toBeVisible();
  });

  test("a student can view memberships page", async ({ page }) => {
    await page.goto("/gymkhana/memberships");
    await expect(page.getByText("My Club Memberships")).toBeVisible();
  });

  test("a student can view polls page", async ({ page }) => {
    await page.goto("/gymkhana/polls");
    await expect(page.getByText("Voting Polls")).toBeVisible();
  });

  for (const path of ADMIN_PAGES) {
    test(`a student who opens /gymkhana/${path} is blocked by route guard`, async ({ page }) => {
      await page.goto(`/gymkhana/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
    });
  }
});
