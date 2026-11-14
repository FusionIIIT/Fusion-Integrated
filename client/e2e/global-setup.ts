import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { type APIRequestContext, type FullConfig, request } from "@playwright/test";

import { type Account, ACCOUNTS, type AccountKey, PASSWORD } from "./accounts";
import { AUTH_DIR, LOGIN_RETRY_MS, LOGIN_TRIES, stateFile } from "./support/session";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const IAM_DIR = resolve(process.env.E2E_IAM_DIR ?? resolve(HERE, "../../../Fusion_System_Administrator"));

function grantRoles(): void {
  const python = resolve(IAM_DIR, "Backend/venv/bin/python");
  if (!existsSync(python)) {
    console.warn(`e2e: no IAM at ${IAM_DIR}; set E2E_IAM_DIR to grant roles, checking them only`);
    return;
  }
  // This repo's settings module and DB_* would override the IAM's own .env.
  const env = Object.fromEntries(Object.entries(process.env)
    .filter(([key]) => key !== "DJANGO_SETTINGS_MODULE" && !key.startsWith("DB_")));
  for (const account of Object.values(ACCOUNTS) as Account[]) {
    for (const designation of account.grants) {
      try {
        execFileSync(python, ["manage.py", "assign_role", "--user", account.username,
          "--designation", designation],
        { cwd: resolve(IAM_DIR, "Backend/backend"), env, stdio: "pipe" });
      } catch (err) {
        const stderr = (err as { stderr?: Buffer }).stderr?.toString().trim() ?? "";
        throw new Error(`e2e: assign_role ${designation} on ${account.username} failed: ${stderr}`);
      }
    }
  }
}

async function rolesOf(api: APIRequestContext): Promise<string[] | null> {
  const me = await api.get("/api/v1/me");
  return me.ok() ? ((await me.json()) as { roles: string[] }).roles : null;
}

// The IAM allows five logins a minute and the API reports a throttled one as a bad password.
async function logIn(api: APIRequestContext, account: Account): Promise<void> {
  for (let attempt = 1; attempt <= LOGIN_TRIES; attempt++) {
    const res = await api.post("/api/v1/auth/login",
      { data: { username: account.username, password: PASSWORD } });
    if (res.ok()) return;
    if (attempt < LOGIN_TRIES) await new Promise((r) => setTimeout(r, LOGIN_RETRY_MS));
  }
  throw new Error(`e2e: ${account.username} cannot sign in. Is the IAM running on a clean `
    + "fusion-dev.dump restore, with this account present?");
}

async function prepare(baseURL: string, key: AccountKey): Promise<void> {
  const account: Account = ACCOUNTS[key];
  const saved = stateFile(key);
  const api = await request.newContext({
    baseURL, storageState: existsSync(saved) ? saved : undefined,
  });
  try {
    let roles = await rolesOf(api);
    const stale = roles !== null && account.grants.some((g) => !roles?.includes(g));
    if (roles === null || stale) {
      await logIn(api, account);
      roles = await rolesOf(api);
    }
    const missing = account.grants.filter((g) => !roles?.includes(g));
    if (missing.length) {
      throw new Error(`e2e: ${account.username} lacks ${missing.join(", ")}. `
        + "Set E2E_IAM_DIR so global setup can grant it, or run assign_role by hand.");
    }
    await api.storageState({ path: saved });
  } finally {
    await api.dispose();
  }
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL ?? "http://localhost:5173";
  const probe = await request.newContext({ baseURL });
  const anonymous = (await probe.get("/api/v1/me")).status();
  await probe.dispose();
  if (anonymous !== 401) {
    throw new Error(`e2e: GET /api/v1/me answered ${anonymous}, expected 401. `
      + "Start the IAM and `make dev` first.");
  }
  grantRoles();
  mkdirSync(AUTH_DIR, { recursive: true });
  for (const key of Object.keys(ACCOUNTS) as AccountKey[]) await prepare(baseURL, key);
}
