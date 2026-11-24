import { expect, signedInAs, test, uniqueName } from "../support/test";
import { ensureTenure, HOD_ID, openDept, pageAs } from "./helpers";

test.describe("department: announcements", () => {
  test.use(signedInAs("deptFaculty"));

  test("UC-DEPT-002/001/003: faculty publishes, a student sees it, the HOD hides it", async ({ page, browser }) => {
    const title = uniqueName("E2E notice");
    await openDept(page, "deptFaculty", "Announcements", "Announcements");
    await page.getByRole("button", { name: "Publish announcement" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Title" }).fill(title);
    await dialog.getByRole("textbox", { name: "Text" }).fill("Lab closed for maintenance.");
    const published = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/department/announcements") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Publish" }).click();
    expect((await published).status()).toBe(201);
    await expect(page.getByText(title)).toBeVisible();

    const student = await pageAs(browser, "deptStudent");
    await openDept(student, "deptStudent", "Announcements", "Announcements");
    await expect(student.getByText(title)).toBeVisible();
    await expect(student.getByRole("button", { name: "Hide" })).toHaveCount(0);
    await student.context().close();

    await ensureTenure(browser, "HOD", HOD_ID);
    const hod = await pageAs(browser, "deptHod");
    await openDept(hod, "deptHod", "Announcements", "Announcements");
    const card = () => hod.locator("div").filter({ hasText: title }).filter({ has: hod.getByText(title) });
    await card().filter({ has: hod.getByRole("button", { name: "Hide" }) }).last()
      .getByRole("button", { name: "Hide" }).click();
    await expect(card().getByText("hidden", { exact: true }).first()).toBeVisible();
    await hod.context().close();
  });
});
