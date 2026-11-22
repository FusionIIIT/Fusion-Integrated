import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { request } from "@playwright/test";
import { expect, signedInAs, test } from "../support/test";

function permissions(operation: "remove" | "restore") {
  if (process.env.HREIS_E2E_IAM_SYNTHETIC !== "1") throw new Error("Synthetic IAM opt-in is required.");
  const iam = resolve(process.env.E2E_IAM_DIR!);
  const script = fileURLToPath(new URL("iam-permissions.py", import.meta.url));
  const env = Object.fromEntries(Object.entries(process.env).filter(([key]) =>
    key !== "DJANGO_SETTINGS_MODULE" && !key.startsWith("DB_")));
  execFileSync(resolve(iam, "Backend/venv/bin/python"), ["manage.py", "shell", "-c",
    `exec(open(${JSON.stringify(script)}).read())`], {
    cwd: resolve(iam, "Backend/backend"), stdio: "pipe",
    env: { ...env, HREIS_E2E_PERMISSION_OPERATION: operation },
  });
}

test.describe("Every HR deep link checks its independent permission", () => {
  test.use(signedInAs("hrEmployee"));
  test.beforeAll(() => permissions("remove"));
  test.afterAll(async ({ baseURL }) => {
    permissions("restore");
    const api = await request.newContext({ baseURL, ...signedInAs("hrEmployee") });
    try {
      const before = await api.get("/api/v1/me");
      const refreshed = await api.patch("/api/v1/me", { data: { active_role: "staff" },
        headers: { "X-CSRF-Token": (await before.json()).csrf_token } });
      expect(refreshed.status()).toBe(200);
      expect((await refreshed.json()).permissions).toContain("hreis.request.view");
    } finally { await api.dispose(); }
  });
  for (const route of ["my-record", "requests", "leave", "claims", "appraisals", "approvals",
    "finance", "administration", "notifications", "audit"]) {
    test(`${route}: a module-granted employee without the permission sees no page controls`, async ({ page }) => {
      const before = await page.request.get("/api/v1/me");
      const csrf = (await before.json()).csrf_token;
      const refreshed = await page.request.patch("/api/v1/me", {
        data: { active_role: "staff" }, headers: { "X-CSRF-Token": csrf },
      });
      expect(refreshed.status()).toBe(200);
      const session = await refreshed.json();
      expect(session.modules).toContain("hreis");
      expect(session.permissions.filter((permission: string) => permission.startsWith("hreis."))).toEqual([]);
      await page.goto(`/hreis/${route}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("button", {
        name: /Apply for leave|LTC request|CPDA request|Annual appraisal|Create employee record|Save record|Record finance|Review|Assign reviewers|Mark as read/,
      })).toHaveCount(0);
    });
  }
});
