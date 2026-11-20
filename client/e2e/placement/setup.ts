import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { type APIRequestContext, expect, type Locator, type Page, request } from "@playwright/test";

import { ACCOUNTS, type AccountKey } from "../accounts";
import { stateFile } from "../support/session";
import { openModuleNav, sidebar, uniqueName } from "../support/test";

export const SEASON = "2026-27";
const BASE = process.env.E2E_BASE_URL ?? "http://localhost:5173";
const API = "/api/v1/placement";

export interface Api {
  get: (path: string) => Promise<unknown>;
  post: (path: string, data?: unknown) => Promise<{ id: number } & Record<string, unknown>>;
  dispose: () => Promise<void>;
}

async function withCsrf(ctx: APIRequestContext, meUrl: string, csrfOf: (body: never) => string,
): Promise<Api> {
  const me = await ctx.get(meUrl);
  expect(me.ok(), `session at ${meUrl}`).toBe(true);
  const token = csrfOf(await me.json() as never);
  return {
    get: async (path) => {
      const res = await ctx.get(`${API}${path}`);
      expect(res.ok(), `GET ${path}: ${await res.text()}`).toBe(true);
      return res.json();
    },
    post: async (path, data = {}) => {
      const res = await ctx.post(`${API}${path}`,
        { data, headers: { "X-CSRF-Token": token } });
      expect(res.ok(), `POST ${path}: ${await res.text()}`).toBe(true);
      return res.json();
    },
    dispose: () => ctx.dispose(),
  };
}

// Setup through the API as an institute account, so each spec drives only its own screen.
export async function apiAs(key: AccountKey): Promise<Api> {
  const ctx = await request.newContext({ baseURL: BASE, storageState: stateFile(key) });
  return withCsrf(ctx, "/api/v1/me", (b: { csrf_token: string }) => b.csrf_token);
}

export async function approvedCompany(office: Api): Promise<number> {
  const company = await office.post("/companies", { name: uniqueName("E2E Co") });
  await office.post(`/companies/${company.id}/approve`, { note: "E2E" });
  return company.id;
}

export function postingBody(extra: Record<string, unknown> = {}) {
  return {
    placement_year: SEASON, title: uniqueName("E2E Role"), kind: "fte",
    description: "Build and run services.", ctc_lpa: "12.00", seats: 2,
    closes_at: new Date(Date.now() + 7 * 864e5).toISOString(),
    eligibility_rule: { gte: ["cpi", 6.0] }, ...extra,
  };
}

export async function publishedPosting(office: Api, companyId: number) {
  const posting = await office.post("/postings", postingBody({ company_id: companyId }));
  await office.post(`/postings/${posting.id}/publish`);
  return posting as { id: number; title: string };
}

// The applicant is registered for the season once; later runs find it already done.
export async function registered(student: Api): Promise<void> {
  const mine = await student.get("/registrations") as { results: { season: string;
    status: string }[] };
  if (!mine.results.some((r) => r.season === SEASON && r.status === "registered")) {
    await student.post("/registrations", { season: SEASON });
  }
}

export async function applied(student: Api, postingId: number) {
  return student.post("/applications/apply", { posting_id: postingId });
}

// A recruiter for a fresh approved company, signed in inside this page's browser context.
export async function recruiterSignedIn(page: Page, office: Api) {
  const companyId = await approvedCompany(office);
  const email = `${uniqueName("hire").replace(/\W+/g, "-")}@example.test`;
  const invite = await office.post("/recruiters/invite", { company_id: companyId, email });
  const password = "E2e-recruiter-pass-9!";
  const anon = await request.newContext({ baseURL: BASE });
  expect((await anon.post(`${API}/recruiters/accept`,
    { data: { token: invite.invite_token, password } })).ok()).toBe(true);
  await anon.dispose();
  const login = await page.request.post(`${API}/recruiters/login`,
    { data: { email, password } });
  expect(login.ok(), "recruiter sign-in").toBe(true);
  return { companyId, email };
}

const IAM_DIR = resolve(process.env.E2E_IAM_DIR
  ?? resolve(fileURLToPath(new URL(".", import.meta.url)), "../../../../Fusion_System_Administrator"));

// The fixture leaves every portal profile incomplete, and PC-BR-001 refuses an incomplete one.
export function profileCompleted(key: AccountKey): void {
  const python = resolve(IAM_DIR, "Backend/venv/bin/python");
  if (!existsSync(python)) return;
  const env = Object.fromEntries(Object.entries(process.env)
    .filter(([k]) => k !== "DJANGO_SETTINGS_MODULE" && !k.startsWith("DB_")));
  execFileSync(python, ["manage.py", "shell", "-c",
    "from iam.models import IamUser; IamUser.objects.filter(username="
    + `${JSON.stringify(ACCOUNTS[key].username)}).update(profile_completed=True)`],
  { cwd: resolve(IAM_DIR, "Backend/backend"), env, stdio: "pipe" });
}

// The group slides open, and a click on a link still clipped by it lands on nothing.
export async function openScreen(page: Page, name: string,
  group = "Placement Cell"): Promise<void> {
  await openModuleNav(page, group);
  const link = sidebar(page).getByRole("link", { name, exact: true });
  await expect(link).toBeInViewport({ ratio: 1 });
  await link.click();
  await expect(link).toHaveAttribute("aria-current", "page");
}

// The picker is a calendar, so a date is chosen as a user does: the 15th of next month.
export async function pickNextMonth(form: Locator, label: string): Promise<void> {
  const page = form.page();
  await form.getByRole("button", { name: label }).click();
  await page.getByRole("button", { name: "Next month" }).click();
  const day = new Date();
  day.setMonth(day.getMonth() + 1, 15);
  const name = `15 ${day.toLocaleString("en-GB", { month: "long" })} ${day.getFullYear()}`;
  await page.getByRole("button", { name, exact: true }).click();
  await page.getByRole("button", { name: "Confirm date and time" }).click();
}

// Through the recruiter's own "New posting" form; it saves a draft.
export async function draftPosting(page: Page, title: string): Promise<void> {
  await page.getByRole("button", { name: "New posting" }).click();
  const dialog = page.getByRole("dialog", { name: "Post a role" });
  await dialog.getByRole("textbox", { name: "Role title" }).fill(title);
  await dialog.getByRole("textbox", { name: "CTC (LPA)" }).fill("12");
  await dialog.getByRole("textbox", { name: "Seats" }).fill("2");
  await pickNextMonth(dialog, "Applications close");
  await dialog.getByRole("textbox", { name: "Role description" }).fill("Build and run services.");
  await dialog.getByRole("textbox", { name: "Minimum CPI" }).fill("6");
  const created = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/placement/postings") && r.request().method() === "POST");
  await dialog.getByRole("button", { name: "Create draft" }).click();
  expect((await created).status()).toBe(201);
  await expect(dialog).toBeHidden();
}
