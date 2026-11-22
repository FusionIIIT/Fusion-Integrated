import { type Page } from "@playwright/test";

import { expect, signedInAs, test } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, local, openDept } from "./helpers";

// A one-minute successor starting exactly when the latest ECE Dept_Admin tenure ends, so every run
// records one and none overlaps or leaves a gap (BR-DEPT-022).
async function successorWindow(page: Page): Promise<{ from: Date; to: Date }> {
  let url: string | null = "/api/v1/department/role-assignments?limit=100";
  let latest = 0;
  while (url) {
    const res = await page.request.get(url);
    expect(res.ok()).toBe(true);
    const data = (await res.json()) as { next: string | null; results: Tenure[] };
    for (const t of data.results) {
      if (t.department === "ECE" && t.role === "dept_admin") latest = Math.max(latest, Date.parse(t.valid_to));
    }
    url = data.next;
  }
  const soon = Math.ceil((Date.now() + 120_000) / 60_000) * 60_000;
  const from = new Date(latest > Date.now() ? latest : soon);
  return { from, to: new Date(from.getTime() + 60_000) };
}

interface Tenure { department: string; role: string; valid_to: string }

test.describe("department: role tenures", () => {
  test.use(signedInAs("deptCentral"));

  test("UC-DEPT-020: the central authority records a Dept_Admin tenure through the UI", async ({ page }) => {
    await openDept(page, "deptCentral", "HOD & Dept_Admin", "HOD & Dept_Admin");
    const { from, to } = await successorWindow(page);
    await page.getByRole("button", { name: "Record tenure" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Department" }).click();
    await page.getByRole("option", { name: /^ECE/ }).click();
    await dialog.getByRole("textbox", { name: "Role" }).click();
    await page.getByRole("option", { name: "Dept_Admin", exact: true }).click();
    await dialog.getByRole("textbox", { name: "Employee user id" }).fill(String(ADMIN_ID));
    await dialog.getByLabel("Starts").fill(local(from));
    await dialog.getByLabel("Ends").fill(local(to));
    const saved = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/department/role-assignments") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save" }).click();
    const res = await saved;
    expect(res.status()).toBe(201);
    const body = (await res.json()) as { department: string; role: string; user_id: number; valid_from: string };
    expect(body).toMatchObject({ department: "ECE", role: "dept_admin", user_id: ADMIN_ID });
    // The form takes whole minutes, so a start that falls mid-minute is entered at that minute.
    expect(new Date(body.valid_from).getTime()).toBe(Math.floor(from.getTime() / 60_000) * 60_000);
    await expect(dialog).toBeHidden();
  });

  test("UC-DEPT-022: the HOD in effect is the department's headship", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await openDept(page, "deptCentral", "Overview", "Computer Science and Engineering");
    await expect(page.getByText("Head of department:")).toBeVisible();
    await expect(page.getByText("No HOD in effect")).toHaveCount(0);
  });
});
