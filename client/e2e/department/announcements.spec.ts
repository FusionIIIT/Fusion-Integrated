import { expect, signedInAs, test } from "../support/test";

test.use(signedInAs("student"));

test("UC-DEPT-001 opens announcements as a student", async ({ page }) => {
  const loaded = page.waitForResponse((response) =>
    new URL(response.url()).pathname === "/api/v1/department/announcements");
  await page.goto("/department/announcements");
  await expect(page.getByRole("heading", { name: "Department announcements" })).toBeVisible();
  expect((await loaded).status()).toBe(200);
});

test("UC-DEPT-007 submits confidential feedback", async ({ page }) => {
  await page.goto("/department/feedback");
  await expect(page.getByRole("heading", { name: "Submit feedback" })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Feedback" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await page.getByRole("textbox", { name: "Feedback" }).fill("Please improve the laboratory access ramp.");
  await page.getByRole("button", { name: "Submit" }).click();
  await expect(page.getByText("Feedback submitted.")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Feedback" })).toHaveValue("");
});

test("student cannot enter staff pages directly", async ({ page }) => {
  for (const path of ["inventory", "stock-requests", "feedback-inbox", "labs", "details"]) {
    await page.goto(`/department/${path}`);
    await expect(page.getByText("Not available to your role")).toBeVisible();
  }
});
