import { expect, openModuleNav, sidebar, signedInAs, test } from "../support/test";

// The plain student's PHC screens, reached through the sidebar (PHC-UC-01, PHC-UC-02).
test.describe("phc: patient pages", () => {
  test.use(signedInAs("student"));

  test("a student sees the doctor schedule without staff controls", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Primary Health Centre");
    await sidebar(page).getByRole("link", { name: "Doctor Schedule" }).click();
    await expect(page.getByRole("heading", { name: "Doctor schedule", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: "New schedule" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /mark available/i })).toHaveCount(0);
  });

  test("a student reads their own records, read-only", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Primary Health Centre");
    await sidebar(page).getByRole("link", { name: "Medical Records" }).click();
    await expect(page.getByRole("heading", { name: "Medical records", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Record visit" })).toHaveCount(0);
  });

  test("a student is offered no reimbursement screen (PHC-BR-04)", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Primary Health Centre");
    await expect(sidebar(page).getByRole("link", { name: "Reimbursements" })).toHaveCount(0);
    await page.goto("/phc/claims");
    await expect(page.getByText("Not available to your role")).toBeVisible();
  });
});
