import { expect, type Page } from "@playwright/test";

import type { AccountKey } from "../accounts";
import { actAs, openModuleNav, sidebar } from "../support/test";

// Act as a role and open one PHC page through the sidebar.
export async function openPhc(page: Page, key: AccountKey, link: string, heading: string) {
  await page.goto("/");
  await actAs(page, key);
  await openModuleNav(page, "Primary Health Centre");
  await sidebar(page).getByRole("link", { name: link }).click();
  await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();
}

// Pick an option from a Mantine Select by its label.
export async function choose(page: Page, label: string, option: string | RegExp) {
  await page.getByRole("textbox", { name: label }).click();
  await page.getByRole("option", { name: option }).first().click();
}

export function waitForWrite(page: Page, path: string) {
  return page.waitForResponse((r) =>
    r.url().includes(`/api/v1/phc/${path}`) && r.request().method() !== "GET");
}
