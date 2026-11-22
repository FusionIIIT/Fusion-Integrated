import { expect, signedInAs, test, uniqueName } from "../support/test";
import { ADMIN_ID, ensureTenure, openDept, pageAs } from "./helpers";

test.describe("department: timetable, labs and people", () => {
  test.use(signedInAs("deptAdmin"));

  test("UC-DEPT-009/018: Dept_Admin adds a slot and a student sees it", async ({ page, browser }) => {
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const course = `E2E${Date.now().toString(36).slice(-6)}`;
    await openDept(page, "deptAdmin", "Timetable", "Timetable");
    await page.getByRole("button", { name: "Add slot" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Course code" }).fill(course);
    await dialog.getByRole("textbox", { name: "Room" }).fill(`R-${course}`);
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("row").filter({ hasText: course })).toBeVisible();

    const student = await pageAs(browser, "deptStudent");
    await openDept(student, "deptStudent", "Timetable", "Timetable");
    await expect(student.getByRole("row").filter({ hasText: course })).toBeVisible();
    await expect(student.getByRole("button", { name: "Add slot" })).toHaveCount(0);
    await openDept(student, "deptStudent", "Overview", "Computer Science and Engineering");
    await student.context().close();
  });

  test("UC-DEPT-017/011: Dept_Admin adds a lab and faculty can see it", async ({ page, browser }) => {
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const lab = uniqueName("E2E lab");
    await openDept(page, "deptAdmin", "Lab Resources", "Lab Resources");
    await page.getByRole("button", { name: "Add lab" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Name" }).fill(lab);
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("row").filter({ hasText: lab })).toBeVisible();

    const faculty = await pageAs(browser, "deptFaculty");
    await openDept(faculty, "deptFaculty", "Lab Resources", "Lab Resources");
    await expect(faculty.getByRole("row").filter({ hasText: lab })).toBeVisible();
    await expect(faculty.getByRole("button", { name: "Edit" })).toHaveCount(0);
    await faculty.context().close();
  });

  test("UC-DEPT-016/015: Dept_Admin adds an alumni profile and faculty see it at the limited tier", async ({ page, browser }) => {
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const name = uniqueName("E2E alum");
    await openDept(page, "deptAdmin", "People", "People");
    await page.getByRole("button", { name: "Add profile" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Kind" }).click();
    await page.getByRole("option", { name: "Alumni" }).click();
    await dialog.getByRole("textbox", { name: "Name" }).fill(name);
    await dialog.getByRole("textbox", { name: "Current position" }).fill("Engineer");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("row").filter({ hasText: name })).toBeVisible();

    const faculty = await pageAs(browser, "deptFaculty");
    await openDept(faculty, "deptFaculty", "People", "People");
    await expect(faculty.getByRole("row").filter({ hasText: name })).toBeVisible();
    await expect(faculty.getByRole("button", { name: "Add profile" })).toHaveCount(0);
    await faculty.context().close();
  });
});
