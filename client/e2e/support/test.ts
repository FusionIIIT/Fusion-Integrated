import { expect, type Page, test as base } from "@playwright/test";

import { ACCOUNTS, type AccountKey, PASSWORD } from "../accounts";
import { LOGIN_RETRY_MS, LOGIN_TRIES, stateFile } from "./session";

// Every test fails on an uncaught page error, a console error or any 5xx from the API.
export const test = base.extend<{ guard: undefined }>({
  guard: [async ({ page }, use) => {
    const problems: string[] = [];
    page.on("pageerror", (err) => problems.push(`uncaught: ${err.message}`));
    page.on("console", (msg) => {
      // A failed request logs this too; the response listener below judges those.
      if (msg.type() === "error" && !msg.text().startsWith("Failed to load resource")) {
        problems.push(`console: ${msg.text()}`);
      }
    });
    page.on("response", (res) => {
      if (res.url().includes("/api/") && res.status() >= 500) {
        problems.push(`${res.status()} ${res.request().method()} ${res.url()}`);
      }
    });
    await use(undefined);
    expect(problems, "uncaught errors, console errors or 5xx responses").toEqual([]);
  }, { auto: true }],
});

export { expect };

// Start a test already signed in, from the session global setup saved for that account.
export function signedInAs(key: AccountKey): { storageState: string } {
  return { storageState: stateFile(key) };
}

// Through the real login form; only tests about signing in should need it.
export async function signIn(page: Page, key: AccountKey): Promise<void> {
  await page.goto("/login");
  await page.getByRole("button", { name: "Proceed to login" }).click();
  await page.getByRole("textbox", { name: /username/i }).fill(ACCOUNTS[key].username);
  await page.getByRole("textbox", { name: /password/i }).fill(PASSWORD);
  await submitUntilSignedIn(page, () => page.getByRole("button", { name: "Sign in" }).click());
}

// The IAM throttles logins and the API calls that a bad password, so a known-good one is retried.
export async function submitUntilSignedIn(page: Page, submit: () => Promise<void>): Promise<void> {
  for (let attempt = 1; attempt <= LOGIN_TRIES; attempt++) {
    const [res] = await Promise.all([
      page.waitForResponse((r) =>
        r.url().endsWith("/api/v1/auth/login") && r.request().method() === "POST"),
      submit(),
    ]);
    if (res.ok()) {
      await expect(page).not.toHaveURL(/\/login/);
      return;
    }
    if (attempt < LOGIN_TRIES) await page.waitForTimeout(LOGIN_RETRY_MS);
  }
  throw new Error(`sign-in still refused after ${LOGIN_TRIES} tries`);
}

export function sidebar(page: Page) {
  return page.getByRole("navigation", { name: "Main navigation" });
}

export async function openSidebar(page: Page): Promise<void> {
  const expand = sidebar(page).getByRole("button", { name: "Expand sidebar" });
  if (await expand.isVisible()) await expand.click();
  await expect(sidebar(page).getByRole("button", { name: "Collapse sidebar" })).toBeVisible();
}

export async function actAs(page: Page, key: AccountKey): Promise<void> {
  await openSidebar(page);
  const role = ACCOUNTS[key].role;
  const picker = sidebar(page).getByRole("combobox", { name: "Switch role" });
  if ((await picker.inputValue()) !== role) {
    const switched = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/me") && r.request().method() === "PATCH");
    await picker.selectOption(role);
    expect((await switched).ok(), `switching to ${role}`).toBe(true);
  }
  await expect(picker).toHaveValue(role);
}

export async function openModuleNav(page: Page, module: string): Promise<void> {
  await openSidebar(page);
  const group = sidebar(page).getByRole("button", { name: module });
  if ((await group.getAttribute("aria-expanded")) !== "true") await group.click();
  await expect(group).toHaveAttribute("aria-expanded", "true");
}
