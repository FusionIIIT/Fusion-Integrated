// Small steps shared by the PMS journeys: reach a page, open a record, fill a modal.
import { type Browser, expect, type Locator, type Page, request } from "@playwright/test";

import { ACCOUNTS, type AccountKey } from "../accounts";
import { stateFile } from "../support/session";
import { actAs, openModuleNav, sidebar } from "../support/test";

export async function go(page: Page, key: AccountKey, link: string): Promise<void> {
  await page.goto("/");
  await actAs(page, key);
  await openModuleNav(page, "Patent Management");
  await sidebar(page).getByRole("link", { name: link }).click();
  await expect(page.getByRole("heading", { name: link, level: 2 })).toBeVisible();
}

// The newest dialog is the modal in front; a drawer behind it is a dialog too.
export function modal(page: Page): Locator {
  return page.getByRole("dialog").last();
}

export async function choose(page: Page, scope: Locator, label: string | RegExp,
  option: string | RegExp): Promise<void> {
  await scope.getByRole("textbox", { name: label }).click();
  await page.getByRole("option", { name: option, exact: typeof option === "string" }).click();
}

// The IAM directory matches usernames, so search by the account's username and pick by name.
export async function person(page: Page, scope: Locator, label: string, key: AccountKey) {
  await scope.getByRole("textbox", { name: label }).fill(ACCOUNTS[key].username);
  await page.getByRole("option", { name: new RegExp(NAMES[key as keyof typeof NAMES]) }).click();
}

export async function openApp(page: Page, title: string): Promise<Locator> {
  const row = page.getByRole("row").filter({ hasText: title }).first();
  await row.getByRole("button", { name: /^Open / }).click();
  const drawer = page.getByRole("dialog", { name: new RegExp(title) });
  await expect(drawer).toBeVisible();
  return drawer;
}

// Submit the modal and wait for the API to answer the given status.
export async function submit(page: Page, button: string, path: RegExp, status = 200) {
  const answered = page.waitForResponse((r) => path.test(r.url())
    && r.request().method() !== "GET");
  await modal(page).getByRole("button", { name: button, exact: true }).click();
  const res = await answered;
  const said = res.status() === status ? "" : await res.text();
  expect(res.status(), `${res.request().method()} ${res.url()} ${said}`).toBe(status);
}

export async function act(page: Page, drawer: Locator, label: string | RegExp) {
  await drawer.getByRole("button", { name: label }).click();
  await expect(modal(page)).toBeVisible();
}

export const PDF = Buffer.from("%PDF-1.4\n1 0 obj << >> endobj\ntrailer << >>\n%%EOF\n");

export async function attachPdf(page: Page, scope: Locator, name: string) {
  const chooser = page.waitForEvent("filechooser");
  await scope.getByRole("button", { name: "PDF file" }).click();
  await (await chooser).setFiles({ name, mimeType: "application/pdf", buffer: PDF });
}

export async function tabTo(page: Page, target: Locator): Promise<void> {
  for (let i = 0; i < 60; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  throw new Error("could not reach the control with Tab");
}

// A second signed-in browser for another account, failing on the same problems the guard does.
export interface Seat { page: Page; close: () => Promise<void> }

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5173";

export async function seat(browser: Browser, key: AccountKey): Promise<Seat> {
  const context = await browser.newContext({ baseURL: BASE_URL, storageState: stateFile(key) });
  // Fail a stuck step with its locator before the whole test times out.
  context.setDefaultTimeout(15_000);
  const page = await context.newPage();
  const problems: string[] = [];
  page.on("pageerror", (err) => problems.push(`uncaught: ${err.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error" && !msg.text().startsWith("Failed to load resource")) {
      problems.push(`console: ${msg.text()}`);
    }
  });
  page.on("response", (res) => {
    if (res.url().includes("/api/") && res.status() >= 500) {
      problems.push(`${res.status()} ${res.request().method()} ${res.url()}`);
    }
  });
  return { page, close: async () => {
    await context.close();
    expect(problems, `${key}: uncaught errors, console errors or 5xx responses`).toEqual([]);
  } };
}

// Preconditions only (settings and rosters), set through the same API the screens use.
export interface Api {
  userId: number;
  get: (path: string) => Promise<unknown>;
  post: (path: string, data: unknown) => Promise<{ status: number; body: unknown }>;
  dispose: () => Promise<void>;
}

export async function api(key: AccountKey): Promise<Api> {
  const ctx = await request.newContext({ baseURL: BASE_URL, storageState: stateFile(key) });
  const me = await ctx.get("/api/v1/me");
  expect(me.ok(), `${key} has a session`).toBe(true);
  const session = (await me.json()) as { csrf_token: string; user: { id: number } };
  const headers = { "X-CSRF-Token": session.csrf_token };
  const role = ACCOUNTS[key].role;
  const switched = await ctx.patch("/api/v1/me", { data: { active_role: role }, headers });
  expect(switched.ok(), `${key} acts as ${role}`).toBe(true);
  return {
    userId: session.user.id,
    get: async (path) => {
      const r = await ctx.get(`/api/v1/pms/${path}`);
      expect(r.ok(), `GET ${path}`).toBe(true);
      return r.json();
    },
    post: async (path, data) => {
      const r = await ctx.post(`/api/v1/pms/${path}`, { data, headers });
      return { status: r.status(), body: await r.json().catch(() => null) };
    },
    dispose: () => ctx.dispose(),
  };
}

interface RosterRow { user_id: number; domain_codes: string[]; valid_to: string | null }

// Put someone on a roster for the e2e area unless they already are; parallel journeys race here.
async function onRoster(pcc: Api, roster: string, userId: number): Promise<void> {
  for (let attempt = 0; attempt < 3; attempt++) {
    const rows = (await pcc.get(roster)) as RosterRow[];
    if (rows.some((r) => r.user_id === userId && r.valid_to == null
      && r.domain_codes.includes(AREA.code))) return;
    const r = await pcc.post(roster, { user_id: userId, domain_codes: [AREA.code] });
    if (r.status === 201) return;
    expect(r.status, JSON.stringify(r.body)).toBe(409);
  }
  throw new Error(`could not put user ${userId} on ${roster}`);
}

export const AREA = { code: "e2e_materials", label: "E2E Materials", ipc_classes: ["H01M"] };

// The office's settings and rosters every journey needs; safe to run again and in parallel.
export async function ensureOffice(): Promise<void> {
  const pcc = await api("pmsPcc");
  const ids: Record<string, number | undefined> = {};
  for (const key of ["pmsPcc", "pmsDirector", "pmsDirector2", "pmsDirector3",
    "pmsAttorney"] as const) {
    const a = key === "pmsPcc" ? pcc : await api(key);
    ids[key] = a.userId;
    if (a !== pcc) await a.dispose();
  }
  for (let attempt = 0; attempt < 3; attempt++) {
    const current = (await pcc.get("policy")) as { version: number;
      payload: Record<string, unknown> & { domains: { code: string }[] } };
    const p = current.payload;
    const ready = p.domains.some((d) => d.code === AREA.code)
      && (p.withdrawal_statuses as string[]).includes("submitted")
      && p.pcc_contact_user_id === ids.pmsPcc && p.auto_routing_enabled === false;
    if (ready) break;
    const res = await pcc.post("policy", { based_on_version: current.version, payload: {
      ...p, domains: [...p.domains.filter((d) => d.code !== AREA.code), AREA],
      cost_threshold: p.cost_threshold ?? "100000.00",
      withdrawal_statuses: ["submitted", "under_review"],
      withdrawal_consent_required: false, pcc_contact_user_id: ids.pmsPcc,
      auto_routing_enabled: false, licensing_route: p.licensing_route ?? { kind: "committee",
        committee_name: "Technology Transfer Committee" } } });
    if (res.status === 201) break;
    expect(res.status, JSON.stringify(res.body)).toBe(409);
  }
  await onRoster(pcc, "directors", ids.pmsDirector!);
  await onRoster(pcc, "directors", ids.pmsDirector2!);
  await onRoster(pcc, "directors", ids.pmsDirector3!);
  await onRoster(pcc, "attorney-panel", ids.pmsAttorney!);
  await pcc.dispose();
}

export const NAMES = { pmsApplicant: "Test User 3851", pmsApplicant2: "Test User 3852", pmsDirector: "Test User 5319",
  pmsDirector2: "Test User 5320", pmsDirector3: "Test User 5321", pmsAttorney: "Test User 2408" } as const;

// The shared StatusBadge prints the raw status with spaces, e.g. "under review".
export async function hasStatus(drawer: Locator, status: string): Promise<void> {
  await expect(drawer.getByText(new RegExp(`^${status}$`, "i")).first()).toBeVisible();
}

export const LONG = "The approach is novel, non-obvious and useful for the stated application area.";

// UC-PMS-001 through the screens: draft, details, one inventor with agreement, a PDF, submit.
export type Applicant = "pmsApplicant" | "pmsApplicant2";

export async function submitNew(page: Page, title: string,
  applicant: Applicant = "pmsApplicant"): Promise<Locator> {
  await go(page, applicant, "My Applications");
  await page.getByRole("button", { name: "New application" }).click();
  await modal(page).getByRole("textbox", { name: "Title" }).fill(title);
  await modal(page).getByRole("textbox", { name: "Abstract" }).fill("A graphene-coated anode.");
  await choose(page, modal(page), "Technical area", "E2E Materials");
  await submit(page, "Save draft", /\/pms\/applications$/, 201);

  const drawer = await openApp(page, title);
  await act(page, drawer, "Edit details");
  await modal(page).getByRole("textbox", { name: "Detailed description" }).fill(LONG);
  await modal(page).getByRole("textbox", { name: "Claims" }).fill("1. An anode coated in graphene.");
  await submit(page, "Save", /\/pms\/applications\/\d+$/);

  await drawer.getByRole("tab", { name: "Inventors" }).click();
  await drawer.getByRole("button", { name: "Edit inventors" }).click();
  await person(page, modal(page), "Institute member", applicant);
  await submit(page, "Save inventors", /\/inventors$/);
  await act(page, drawer, `Record agreement: ${NAMES[applicant]}`);
  await modal(page).getByRole("textbox", { name: "Agreement reference" }).fill("AGR-E2E-1");
  await modal(page).getByRole("checkbox", { name: "Consent to filing recorded" }).check();
  await submit(page, "Record", /\/agreement$/);
  await expect(drawer.getByRole("cell", { name: "AGR-E2E-1" })).toBeVisible();

  await drawer.getByRole("tab", { name: "Documents" }).click();
  await drawer.getByRole("button", { name: "Upload document" }).click();
  await attachPdf(page, modal(page), "specification.pdf");
  await modal(page).getByRole("textbox", { name: "Title" }).fill("Complete specification");
  await choose(page, modal(page), "Kind", /Specification/);
  await choose(page, modal(page), "Sensitivity", /Restricted/);
  await submit(page, "Upload", /\/documents$/, 201);
  await expect(drawer.getByText("Complete specification")).toBeVisible();

  await act(page, drawer, "Submit application");
  await submit(page, "Submit", /\/submit$/);
  await hasStatus(drawer, "submitted");
  await expect(page.getByRole("dialog", { name: /PMS-\d{4}-\d{5}/ })).toBeVisible();
  return drawer;
}

// UC-PMS-007 through the screens: PCC_ADMIN gives the review to the named Director.
export async function assignDirector(browser: Browser, title: string,
  director: "pmsDirector" | "pmsDirector2" | "pmsDirector3", label = "Assign Director"): Promise<void> {
  const { page, close } = await seat(browser, "pmsPcc");
  await go(page, "pmsPcc", "Oversight");
  await page.getByRole("textbox", { name: "Search by title or reference" }).fill(title);
  const drawer = await openApp(page, title);
  await act(page, drawer, label);
  await choose(page, modal(page), "Director", new RegExp(NAMES[director]));
  await submit(page, "Assign", /\/assign-director$/);
  await hasStatus(drawer, "under review");
  await close();
}

// UC-PMS-008 through the screens: the assigned Director records a decision.
export async function decide(browser: Browser, title: string,
  director: "pmsDirector" | "pmsDirector2", decision: string): Promise<void> {
  const { page, close } = await seat(browser, director);
  await go(page, director, "Reviews");
  const drawer = await openApp(page, title);
  await act(page, drawer, "Record decision");
  await choose(page, modal(page), "Decision", decision);
  await modal(page).getByRole("textbox", { name: /Justification/ }).fill(LONG);
  await submit(page, "Record decision", /\/review$/);
  await close();
}
