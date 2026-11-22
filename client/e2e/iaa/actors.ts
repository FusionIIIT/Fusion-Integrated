// Helpers for the IAA specs: several people act on one item in turn, each in their own
// signed-in browser context, switched to the role the step needs with `actAs`.
import { type Browser, type BrowserContext, type Page, type Response } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, expect, openModuleNav, sidebar, signedInAs } from "../support/test";

export const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";
export const MODULE_LABEL = "Accounts & Audits";
// The department must be the HoD's own: approvers see only their department's items.
export const DEPARTMENT = process.env.E2E_IAA_DEPARTMENT ?? "CSE";

export interface Actor { page: Page; context: BrowserContext; problems: string[] }

// The harness watches the test's own page; this watches the others the same way.
function watch(page: Page, problems: string[]): void {
  page.on("pageerror", (err) => problems.push(`uncaught: ${err.message}`));
  page.on("response", (res) => {
    if (res.url().includes("/api/") && res.status() >= 500) {
      problems.push(`${res.status()} ${res.request().method()} ${res.url()}`);
    }
  });
}

// Opens the module as `key`, already acting in that account's role.
export async function enter(browser: Browser, key: AccountKey): Promise<Actor> {
  const context = await browser.newContext({ ...signedInAs(key), baseURL: BASE_URL });
  const page = await context.newPage();
  const problems: string[] = [];
  watch(page, problems);
  await page.goto("/");
  await actAs(page, key);
  await openModuleNav(page, MODULE_LABEL);
  return { page, context, problems };
}

export async function finish(...actors: Actor[]): Promise<void> {
  for (const a of actors) {
    expect(a.problems, "uncaught errors or 5xx responses").toEqual([]);
    await a.context.close();
  }
}

export async function openPage(page: Page, link: string, heading: string): Promise<void> {
  await sidebar(page).getByRole("link", { name: link }).click();
  await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();
}

// The row for one item, found by the unique title the test gave it.
export function rowFor(page: Page, text: string) {
  return page.getByRole("row", { name: /^Open (request|TA claim) \d+$/ }).filter({ hasText: text });
}

export async function openItem(page: Page, text: string): Promise<void> {
  await rowFor(page, text).click();
  await expect(page.getByRole("dialog").getByText(/^(Request|TA claim) #\d+$/)).toBeVisible();
}

export async function closeDrawer(page: Page): Promise<void> {
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
}

// The POST to `suffix` under /api/v1/iaa/, awaited alongside the click that causes it.
export function posted(page: Page, suffix: RegExp): Promise<Response> {
  return page.waitForResponse((r) =>
    r.request().method() === "POST" && suffix.test(r.url().split("?")[0] ?? ""));
}

export async function clickAndExpectOk(
  page: Page, suffix: RegExp, click: () => Promise<void>,
): Promise<void> {
  const response = posted(page, suffix);
  await click();
  const res = await response;
  expect(res.ok(), `${res.request().method()} ${res.url()} answered ${res.status()}`).toBe(true);
}
