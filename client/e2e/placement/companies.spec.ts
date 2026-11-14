import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("placement: companies", () => {
  test.use(signedInAs("placementOfficer"));

  test("a placement officer registers a company and sees it pending approval", async ({ page }) => {
    const name = uniqueName("E2E Company");

    await page.goto("/");
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "Placement Cell");
    await sidebar(page).getByRole("link", { name: "Companies" }).click();
    await expect(page.getByRole("heading", { name: "Companies", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Register company" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Company name" }).fill(name);
    await dialog.getByRole("textbox", { name: "Sector" }).fill("IT");
    await dialog.getByRole("textbox", { name: "HQ city" }).fill("Jabalpur");
    await dialog.getByRole("textbox", { name: "Website" }).fill("https://example.com");
    await dialog.getByRole("textbox", { name: "Name", exact: true }).fill("E2E Contact");
    await dialog.getByRole("textbox", { name: "Email", exact: true }).fill("contact@example.com");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/placement/companies") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Register" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: name });
    await expect(row).toBeVisible();
    await expect(row).toContainText(/pending/i);
  });

  test.describe("as a student", () => {
    test.use(signedInAs("student"));

    test("a student who opens the page directly is told it is not for them", async ({ page }) => {
      await page.goto("/placement/companies");
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  });
});
