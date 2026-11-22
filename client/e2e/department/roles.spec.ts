import { expect, signedInAs, test } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, local, openDept } from "./helpers";

// A one-minute tenure in its own future minute, so every run records one and none overlaps another.
function ownWindow(): { from: Date; to: Date } {
  const minute = Math.floor(Date.now() / 60_000);
  const from = new Date(Date.UTC(2040, 0, 1) + minute * 60_000);
  return { from, to: new Date(from.getTime() + 60_000) };
}

test.describe("department: role tenures", () => {
  test.use(signedInAs("deptCentral"));

  test("UC-DEPT-020: the central authority records a Dept_Admin tenure through the UI", async ({ page }) => {
    const { from, to } = ownWindow();
    await openDept(page, "deptCentral", "HOD & Dept_Admin", "HOD & Dept_Admin");
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
    expect(new Date(body.valid_from).getTime()).toBe(from.getTime());
    await expect(dialog).toBeHidden();
  });

  test("UC-DEPT-022: the HOD in effect is the department's headship", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await openDept(page, "deptCentral", "Overview", "Computer Science and Engineering");
    await expect(page.getByText("Head of department:")).toBeVisible();
    await expect(page.getByText("No HOD in effect")).toHaveCount(0);
  });
});
