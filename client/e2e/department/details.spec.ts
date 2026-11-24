import { expect, signedInAs, test, uniqueName } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, openDept, pageAs } from "./helpers";

test.describe("department: details", () => {
  test.use(signedInAs("deptAdmin"));

  test("UC-DEPT-010/012: Dept_Admin proposes core policies and the HOD approves them", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const policy = uniqueName("E2E policy");
    await openDept(page, "deptAdmin", "Overview", "Computer Science and Engineering");
    await page.getByRole("button", { name: "Propose official change" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Detail" }).click();
    await page.getByRole("option", { name: "Core policies" }).click();
    await dialog.getByRole("textbox", { name: "Proposed value" }).fill(policy);
    const proposed = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/department/official-changes") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save" }).click();
    const status = (await proposed).status();
    expect([201, 409]).toContain(status);  // 409: another run's proposal still waits for the HOD

    const hod = await pageAs(browser, "deptHod");
    await openDept(hod, "deptHod", "Overview", "Computer Science and Engineering");
    // A 409 means an earlier run's proposal is still waiting; the HOD decides that one instead.
    const waiting = hod.getByRole("row").filter({ hasText: status === 201 ? policy : "pending" }).first();
    const proposal = status === 201 ? policy : (await waiting.getByRole("cell").nth(1).innerText());
    const row = hod.getByRole("row").filter({ hasText: proposal }).first();
    await row.getByRole("button", { name: "Approve" }).click();
    await expect(row).toContainText("approved");
    if (status === 201) await expect(hod.getByText(policy).first()).toBeVisible();
    await hod.context().close();
  });
});
