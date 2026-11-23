import { expect, signedInAs, test } from "../support/test";

// Guarded module routes, opened directly by a user without filetracking permissions.
const GUARDED_PAGES = ["inbox", "outbox", "create", "archive", "governance"];

test.describe("filetracking: guarded route access", () => {
  test.use(signedInAs("student"));

  for (const path of GUARDED_PAGES) {
    test(`a student opening /filetracking/${path} receives not permitted notification`, async ({
      page,
    }) => {
      await page.goto(`/filetracking/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
