import { ACCOUNTS, PASSWORD } from "./accounts";
import {
  expect, openModuleNav, sidebar, signIn, submitUntilSignedIn, test, uniqueName,
} from "./support/test";

test.describe("sign-in", () => {
  // Real logins share the IAM's five-a-minute budget, so these may wait out a throttle.
  test.describe.configure({ timeout: 90_000 });

  // A fresh unknown user each run: the IAM locks accounts that keep failing, and answers alike.
  test("wrong credentials are refused and the user stays on the login page", async ({ page }) => {
    await page.goto("/login");
    await page.getByRole("button", { name: "Proceed to login" }).click();
    await page.getByRole("textbox", { name: /username/i })
      .fill(uniqueName("e2e-nobody").replace(/\s/g, "-"));
    await page.getByRole("textbox", { name: /password/i }).fill(`${PASSWORD}-wrong`);
    // Global setup's logins can use up the IAM's budget, so a 429 is waited out first.
    for (let attempt = 1; ; attempt++) {
      const [res] = await Promise.all([
        page.waitForResponse((r) => r.url().endsWith("/api/v1/auth/login")),
        page.getByRole("button", { name: "Sign in" }).click(),
      ]);
      if (res.status() !== 429 || attempt === 3) {
        expect(res.status()).toBe(401);
        break;
      }
      await expect(page.getByRole("alert")).toContainText("Too many sign-in attempts");
      await page.waitForTimeout((Number(res.headers()["retry-after"]) + 1) * 1000);
    }
    await expect(page.getByRole("alert")).toContainText("Incorrect username or password");
    await expect(page).toHaveURL(/\/login/);
  });

  test("a student sees only student screens, then signs out", async ({ page }) => {
    await signIn(page, "student");
    await openModuleNav(page, "Placement Cell");

    const links = sidebar(page).getByRole("link");
    await expect(links).toHaveText(
      ["Season Registration", "My Profile", "Opportunities", "My Applications", "My Offers",
        "Reports"]);

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
