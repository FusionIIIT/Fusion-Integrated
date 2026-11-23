import { expect, signedInAs, test } from "../support/test";

// Pages opened directly by someone the sidebar never offered them to.
const REFUSED = {
  student: ["admin", "reports"],
  facultyCouncillor: ["memberships", "polls", "manage", "admin"],
} as const;

for (const [account, paths] of Object.entries(REFUSED)) {
  test.describe(`gymkhana: pages not for ${account}`, () => {
    test.use(signedInAs(account as keyof typeof REFUSED));

    for (const path of paths) {
      test(`${account} who opens /gymkhana/${path} is told it is not for them`, async ({ page }) => {
        await page.goto(`/gymkhana/${path}`);
        await expect(page.getByText("Not available to your role")).toBeVisible();
        await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
      });
    }
  });
}

test.describe("gymkhana: pages every guard must also let through", () => {
  test.use(signedInAs("student"));

  for (const [path, heading] of [
    ["clubs", "Gymkhana Clubs"], ["memberships", "My Club Memberships"],
    ["polls", "Voting Polls"], ["calendar", "Events & Sessions"], ["manage", "Club Management"],
  ] as const) {
    test(`a student opens /gymkhana/${path}`, async ({ page }) => {
      await page.goto(`/gymkhana/${path}`);
      await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();
    });
  }
});
