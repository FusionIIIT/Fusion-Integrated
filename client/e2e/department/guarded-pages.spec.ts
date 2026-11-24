import { type AccountKey } from "../accounts";
import { expect, signedInAs, test } from "../support/test";

// Each guarded page, opened directly by a granted role whose nav permission it lacks.
const CASES: { account: AccountKey; paths: string[] }[] = [
  { account: "deptStudent", paths: ["inventory", "labs", "roles"] },
  { account: "deptCentral", paths: ["announcements", "feedback", "timetable", "profiles", "inventory", "labs"] },
];

for (const { account, paths } of CASES) {
  test.describe(`department: guarded pages for ${account}`, () => {
    test.use(signedInAs(account));

    for (const path of paths) {
      test(`${account} who opens /department/${path} is told it is not for them`, async ({ page }) => {
        await page.goto(`/department/${path}`);
        await expect(page.getByText("Not available to your role")).toBeVisible();
        await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
      });
    }
  });
}
