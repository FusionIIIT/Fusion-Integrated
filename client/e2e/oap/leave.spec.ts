import {
  expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("oap: student leave", () => {
  test.use(signedInAs("student"));

  test("a student views the leave procedure page and submits an application", async ({ page }) => {
    const reasonText = uniqueName("Attending National Symposium");

    await page.goto("/");
    await openModuleNav(page, "Other Academic Procedures");
    await sidebar(page).getByRole("link", { name: "Student Leave" }).click();
    await expect(page.getByRole("heading", { name: "Student Leave Applications", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Apply for Leave" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Start Date" }).fill("2026-12-01");
    await dialog.getByRole("textbox", { name: "End Date" }).fill("2026-12-05");
    await dialog.getByRole("textbox", { name: "Reason for Leave" }).fill(reasonText);

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/oap/leave") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Submit Application" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: reasonText });
    await expect(row).toBeVisible();
    await expect(row).toContainText(/pending/i);
  });
});
