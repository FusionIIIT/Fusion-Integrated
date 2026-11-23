import type { Browser, Locator, Page } from "@playwright/test";

import { ACCOUNTS } from "../accounts";
import {
  actAs, expect as baseExpect, openModuleNav, sidebar, signedInAs, uniqueName,
} from "../support/test";

const expect = baseExpect.configure({ timeout: 20_000 });

export async function openPage(page: Page, link: string, heading: string): Promise<void> {
  await openModuleNav(page, "Gymkhana");
  await sidebar(page).getByRole("link", { name: link }).click();
  await expect(page.getByRole("heading", { name: heading, level: 2 })).toBeVisible();
}

export async function pick(scope: Page | Locator, label: string, username: string): Promise<void> {
  const field = scope.getByRole("textbox", { name: label, exact: true });
  await field.fill(username);
  const page = "page" in scope ? scope.page() : scope;
  await page.getByRole("option", { name: `(${username})` }).click();
}

export async function choose(scope: Locator, label: string, option: string): Promise<void> {
  await scope.getByRole("textbox", { name: label }).click();
  await scope.page().getByRole("option", { name: option, exact: true }).click();
}

/** The Student Admin establishes a club through the UI, and approves it unless told not to. */
export async function establishClub(page: Page, approve = true): Promise<string> {
  const name = uniqueName("E2E Club");
  await page.goto("/");
  await actAs(page, "studentAdmin");
  await openPage(page, "Club Approvals", "Club Administration");
  await page.getByRole("button", { name: "Create club" }).click();
  const form = page.getByRole("dialog");
  await form.getByRole("textbox", { name: "Club name" }).fill(name);
  await choose(form, "Category", "Technical");
  await pick(form, "Coordinator", ACCOUNTS.clubHead.username);
  await pick(form, "Co-coordinator", ACCOUNTS.studentAdmin.username);
  await pick(form, "Faculty Councillor", ACCOUNTS.facultyCouncillor.username);
  await form.getByRole("button", { name: "Create", exact: true }).click();
  await expect(form).toBeHidden();
  if (approve) await approveClub(page, name);
  return name;
}

export async function approveClub(page: Page, name: string): Promise<void> {
  await find(page, page.getByRole("button", { name: `Review ${name}` }));
  await page.getByRole("button", { name: `Review ${name}` }).click();
  const review = page.getByRole("dialog");
  await review.getByRole("button", { name: "Approve club" }).click();
  await expect(review).toBeHidden();
}

/** Lists are paged, so another run's rows can push this one further down. */
export async function find(page: Page, target: Locator): Promise<void> {
  const more = page.getByRole("button", { name: "Load more" });
  await expect(target.or(more).first()).toBeVisible();
  while (!(await target.first().isVisible()) && (await more.isVisible())) {
    const loaded = page.waitForResponse((r) => r.url().includes("cursor="));
    await more.click();
    await loaded;
    // The last page takes the button away, so wait for it to stop loading, not to be enabled.
    await expect(more.and(page.locator(":disabled"))).toHaveCount(0);
  }
  await expect(target.first()).toBeVisible();
}

/** A confirmed club, made in the Student Admin's own browser session. */
export async function confirmedClub(browser: Browser): Promise<string> {
  const context = await browser.newContext(signedInAs("studentAdmin"));
  try {
    return await establishClub(await context.newPage());
  } finally {
    await context.close();
  }
}

export async function manage(page: Page, club: string, tab: string): Promise<void> {
  await page.goto("/");
  await openPage(page, "Club Management", "Club Management");
  await page.getByRole("textbox", { name: "Club", exact: true }).click();
  await page.getByRole("option", { name: club, exact: true }).click();
  await page.getByRole("tab", { name: tab }).click();
}

export async function asAccount<T>(
  browser: Browser, key: keyof typeof ACCOUNTS, act: (page: Page) => Promise<T>,
): Promise<T> {
  const context = await browser.newContext(signedInAs(key));
  try {
    const page = await context.newPage();
    await page.goto("/");
    return await act(page);
  } finally {
    await context.close();
  }
}

/** A slot no other test or earlier run is likely to hold. */
export function freeSlot(): { date: string; start: string; end: string } {
  const day = new Date(Date.now() + (30 + Math.floor(Math.random() * 20_000)) * 86_400_000);
  return { date: day.toISOString().slice(0, 10), start: "10:00", end: "11:00" };
}

export const PDF = {
  name: "paper.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-1.4 e2e"),
};
