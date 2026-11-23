import type { Locator, Page } from "@playwright/test";

import { actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName } from "../support/test";

test.use(signedInAs("student"));

test("UC-DEPT-001 opens announcements as a student", async ({ page }) => {
  const loaded = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/department/announcements");
  await page.goto("/");
  await actAs(page, "student");
  await openModuleNav(page, "Department");
  await sidebar(page).getByRole("link", { name: "Announcements" }).click();
  await expect(page.getByRole("heading", { name: "Department announcements" })).toBeVisible();
  expect((await loaded).status()).toBe(200);
});

test("UC-DEPT-007 submits confidential feedback", async ({ page }) => {
  await page.goto("/");
  await actAs(page, "student");
  await openModuleNav(page, "Department");
  const link = sidebar(page).getByRole("link", { name: "Submit feedback" });
  await tabTo(page, link);
  await page.keyboard.press("Enter");
  const field = page.getByRole("textbox", { name: "Feedback" });
  await tabTo(page, field);
  await page.keyboard.type(uniqueName("Repair laboratory ramp"));
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Submit" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByText("Feedback submitted.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Feedback" })).toHaveValue("");
});

test("student cannot enter staff pages directly", async ({ page }) => {
  for (const path of ["inventory", "stock-requests", "feedback-inbox", "labs", "details"]) {
    await page.goto(`/department/${path}`);
    await expect(page.getByText("Not available to your role")).toBeVisible();
    await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
  }
});

test.describe("head of department direct access", () => {
  test.use(signedInAs("departmentHead"));
  test("denies feedback submission and the cohort timetable", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "departmentHead");
    for (const path of ["feedback", "timetable"]) {
      await page.goto(`/department/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    }
  });
});

async function tabTo(page: Page, target: Locator) {
  await expect(target).toBeVisible();
  for (let i = 0; i < 80; i++) {
    if (await target.evaluate((element) => element === document.activeElement)) return;
    await page.keyboard.press("Tab");
  }
  await expect(target).toBeFocused();
}
