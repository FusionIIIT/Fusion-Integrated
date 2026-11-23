import { expect, signedInAs, test } from "../support/test";

// Every PHC route a student is refused, opened directly. The other four (schedule, advisories,
// records, notifications) are held by every role through its basic kind, so no account lacks them.
const NOT_FOR_STUDENTS = ["claims", "inventory", "requisitions", "ambulance", "reports"];

test.describe("phc: guarded pages, as a student", () => {
  test.use(signedInAs("student"));

  for (const path of NOT_FOR_STUDENTS) {
    test(`a student who opens /phc/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/phc/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
