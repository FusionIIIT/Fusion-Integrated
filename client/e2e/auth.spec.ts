import { ACCOUNTS, PASSWORD } from "./accounts";
import { expect, openModuleNav, sidebar, signIn, submitUntilSignedIn, test } from "./support/test";

test.describe("sign-in", () => {
  // Real logins share the IAM's five-a-minute budget, so these may wait out a throttle.
  test.describe.configure({ timeout: 90_000 });

  test("a wrong password is refused and the user stays on the login page", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Proceed to login" }).click();
    await page.getByRole("textbox", { name: /username/i }).fill(ACCOUNTS.student.username);
    await page.getByRole("textbox", { name: /password/i }).fill(`${PASSWORD}-wrong`);
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page.getByRole("alert")).toContainText("Incorrect username or password");
    await expect(page).toHaveURL(/\/login/);
  });

  test("a student sees only student screens, then signs out", async ({ page }) => {
    await signIn(page, "student");
    await openModuleNav(page, "Placement Cell");

    const links = sidebar(page).getByRole("link");
    await expect(links).toHaveText(
      ["Season Registration", "Opportunities", "My Applications", "My Offers"]);

    await links.filter({ hasText: "Opportunities" }).click();
    await expect(page.getByRole("heading", { name: "Opportunities", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/login/);
  });

  test("a student can sign in with the keyboard alone", async ({ page }) => {
    await page.goto("/login");
    const proceed = page.getByRole("button", { name: "Proceed to login" });
    await expect(proceed).toBeVisible();
    await tabTo(page, proceed);
    await page.keyboard.press("Enter");

    const username = page.getByRole("textbox", { name: /username/i });
    await tabTo(page, username);
    await page.keyboard.type(ACCOUNTS.student.username);
    await page.keyboard.press("Tab");
    const password = page.getByRole("textbox", { name: /password/i });
    await expect(password).toBeFocused();
    await page.keyboard.type(PASSWORD);

    // A refused attempt moves focus to the alert, so each try tabs back first.
    await submitUntilSignedIn(page, async () => {
      await tabTo(page, password);
      await page.keyboard.press("Enter");
    });
  });
});

async function tabTo(page: import("@playwright/test").Page,
  target: import("@playwright/test").Locator): Promise<void> {
  for (let i = 0; i < 15; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}
