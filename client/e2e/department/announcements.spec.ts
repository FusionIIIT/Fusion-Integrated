import { expect, signedInAs, test } from "../support/test";

test.use(signedInAs("student"));

test("UC-DEPT-001 opens announcements as a student", async ({ page }) => {
  const loaded = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/department/announcements");
  await page.goto("/department/announcements");
  await expect(page.getByRole("heading", { name: "Department announcements" })).toBeVisible();
  expect((await loaded).status()).toBe(200);
});

test("UC-DEPT-007 opens the student's confidential feedback form", async ({ page }) => {
  await page.goto("/department/feedback");
  await expect(page.getByRole("heading", { name: "Submit feedback" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Feedback" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
});
