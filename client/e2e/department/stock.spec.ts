import { expect, signedInAs, test, uniqueName } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, openDept, pageAs } from "./helpers";

test.describe("department: stock", () => {
  test.use(signedInAs("deptAdmin"));

  test("UC-DEPT-019/004/005/006/011: stock is added, requested, approved, issued and seen", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const item = uniqueName("E2E kit");

    await openDept(page, "deptAdmin", "Inventory & Stock", "Inventory & Stock");
    await page.getByRole("button", { name: "Add item" }).click();
    let dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Item name" }).fill(item);
    await dialog.getByRole("textbox", { name: "Quantity received" }).fill("10");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("row").filter({ hasText: item }).first()).toContainText("10");

    const faculty = await pageAs(browser, "deptFaculty");
    await openDept(faculty, "deptFaculty", "Inventory & Stock", "Inventory & Stock");
    await faculty.getByRole("button", { name: "Request stock" }).click();
    dialog = faculty.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Item" }).click();
    await faculty.getByRole("option", { name: new RegExp(item) }).click();
    await dialog.getByRole("textbox", { name: "Quantity" }).fill("3");
    await dialog.getByRole("button", { name: "Submit request" }).click();
    await expect(faculty.getByRole("row").filter({ hasText: item }).filter({ hasText: "pending hod" })).toBeVisible();

    const hod = await pageAs(browser, "deptHod");
    await openDept(hod, "deptHod", "Inventory & Stock", "Inventory & Stock");
    await hod.getByRole("row").filter({ hasText: item }).filter({ hasText: "pending hod" })
      .getByRole("button", { name: "Approve" }).click();
    await expect(hod.getByRole("row").filter({ hasText: item }).filter({ hasText: "approved" })).toBeVisible();
    await hod.context().close();

    await page.reload();
    await page.getByRole("row").filter({ hasText: item }).filter({ hasText: "approved" })
      .getByRole("button", { name: "Issue" }).click();
    await expect(page.getByRole("row").filter({ hasText: item }).filter({ hasText: "issued" })).toBeVisible();
    await expect(page.getByRole("row").filter({ hasText: item }).filter({ hasText: "7 unit" })).toBeVisible();

    await faculty.reload();
    await expect(faculty.getByRole("row").filter({ hasText: item }).filter({ hasText: "issued" })).toBeVisible();
    await faculty.context().close();
  });
});
