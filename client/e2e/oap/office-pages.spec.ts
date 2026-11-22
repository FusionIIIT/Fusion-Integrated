import { expect, signedInAs, test } from "../support/test";

// The office's pages, opened directly by someone the sidebar never offered them to.
const OFFICE_PAGES = ["approvals", "admin/bonafide", "admin/no-dues"];

test.describe("oap: office pages", () => {
  test.use(signedInAs("student"));

  for (const path of OFFICE_PAGES) {
    test(`a student who opens /oap/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/oap/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
