import { type Browser, type Page } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { stateFile } from "../support/session";
import { actAs, expect, openModuleNav, sidebar } from "../support/test";

// ERP user ids of the CSE office accounts in fusion-dev.dump (accounts.ts).
export const HOD_ID = 5350;
export const ADMIN_ID = 5411;

// A second signed-in role in the same test; it fails on any 5xx, as the guarded page does.
export async function pageAs(browser: Browser, key: AccountKey): Promise<Page> {
  const context = await browser.newContext({ storageState: stateFile(key) });
  const page = await context.newPage();
  page.on("response", (res) => {
    if (res.url().includes("/api/") && res.status() >= 500) {
      throw new Error(`${res.status()} ${res.request().method()} ${res.url()}`);
    }
  });
  return page;
}

// Reach a Department screen the way a person would: role switcher, then the sidebar.
export async function openDept(page: Page, key: AccountKey, link: string, heading: string): Promise<void> {
  await page.goto("/");
  await actAs(page, key);
  await openModuleNav(page, "Department");
  await sidebar(page).getByRole("link", { name: link }).click();
  await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();
}

function local(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
    + `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// The central authority records a CSE tenure through the UI unless one is already in effect.
export async function ensureTenure(browser: Browser, role: "HOD" | "Dept_Admin", userId: number): Promise<void> {
  const page = await pageAs(browser, "deptCentral");
  await openDept(page, "deptCentral", "HOD & Dept_Admin", "HOD & Dept_Admin");
  await expect(page.getByText("Loading…")).toHaveCount(0);
  const current = page.getByRole("row")
    .filter({ hasText: "CSE" }).filter({ hasText: role }).filter({ hasText: String(userId) })
    .filter({ hasText: "in effect" });
  if (await current.count() === 0) {
    await page.getByRole("button", { name: "Record tenure" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Department" }).click();
    await page.getByRole("option", { name: /^CSE/ }).click();
    await dialog.getByRole("textbox", { name: "Role" }).click();
    await page.getByRole("option", { name: role, exact: true }).click();
    await dialog.getByRole("textbox", { name: "Employee user id" }).fill(String(userId));
    const now = new Date();
    await dialog.getByLabel("Starts").fill(local(now));
    await dialog.getByLabel("Ends").fill(local(new Date(now.getTime() + 365 * 86_400_000)));
    const saved = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/department/role-assignments") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save" }).click();
    // 409: a parallel worker recorded the same tenure first, and the overlap was refused.
    expect([201, 409]).toContain((await saved).status());
    await page.reload();
    await expect(current.first()).toBeVisible();
  }
  await page.context().close();
}
