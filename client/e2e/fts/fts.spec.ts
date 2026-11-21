import { expect, signedInAs, test } from "../support/test";

const FTS_PAGES = ["inbox", "outbox", "drafts", "create", "governance"] as const;

test.describe("fts: student route guards", () => {
  test.use(signedInAs("student"));

  for (const path of FTS_PAGES) {
    test(`a student who opens /fts/${path} is refused by client route guard`, async ({ page }) => {
      await page.goto(`/fts/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
