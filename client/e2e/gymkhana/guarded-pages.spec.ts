import { expect, signedInAs, test } from "../support/test";

// Each page opened directly by a role whose sidebar never offered it.
const NOT_FOR_STUDENTS = ["administration", "reports"];
const NOT_FOR_FACULTY = ["clubs", "polls", "schedule", "my-clubs", "administration"];

test.describe("gymkhana: pages a student may not open", () => {
  test.use(signedInAs("student"));
  for (const path of NOT_FOR_STUDENTS) {
    test(`a student who opens /gymkhana/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/gymkhana/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});

test.describe("gymkhana: pages a faculty member may not open", () => {
  test.use(signedInAs("gymCouncillor"));
  for (const path of NOT_FOR_FACULTY) {
    test(`faculty who opens /gymkhana/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/gymkhana/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
