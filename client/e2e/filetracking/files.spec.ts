import {
  actAs,
  expect,
  openModuleNav,
  sidebar,
  signedInAs,
  test,
  uniqueName,
} from "../support/test";

test.describe("filetracking: files lifecycle", () => {
  test.use(signedInAs("placementOfficer"));

  test("creates a new file directly into circulation", async ({ page }) => {
    const subject = uniqueName("E2E Requisition File");

    await page.goto("/");
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "File Tracking");
    await sidebar(page).getByRole("link", { name: "Create File" }).click();
    await expect(page.getByRole("heading", { name: "Create New File", level: 2 })).toBeVisible();

    await page.getByLabel("File Subject").fill(subject);
    await page.getByLabel("Initial Note / Description").fill("Official requisition note submitted for review.");
    await page.getByLabel("Recipient Employee ID").fill("112");

    const created = page.waitForResponse(
      (r) => r.url().includes("/api/v1/filetracking/files/") && r.request().method() === "POST"
    );
    await page.getByRole("button", { name: "Circulate File" }).click();
    expect((await created).status()).toBe(201);

    await expect(page).toHaveURL(/\/filetracking\/(outbox|inbox)/);
  });

  test("creates a draft file without circulating", async ({ page }) => {
    const subject = uniqueName("E2E Draft Proposal");

    await page.goto("/");
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "File Tracking");
    await sidebar(page).getByRole("link", { name: "Create File" }).click();
    await expect(page.getByRole("heading", { name: "Create New File", level: 2 })).toBeVisible();

    await page.getByLabel("File Subject").fill(subject);
    await page.getByLabel("Initial Note / Description").fill("Draft working notes for annual sports festival.");
    await page.getByLabel("Save as draft (will not be circulated yet)").check();

    await expect(page.getByLabel("Recipient Employee ID")).toBeHidden();
    const created = page.waitForResponse(
      (r) => r.url().includes("/api/v1/filetracking/files/") && r.request().method() === "POST"
    );
    await page.getByRole("button", { name: "Save Draft" }).click();
    expect((await created).status()).toBe(201);

    await expect(page).toHaveURL(/\/filetracking\/inbox/);
  });

  test("views inbox and outbox file registries", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "File Tracking");

    await sidebar(page).getByRole("link", { name: "Inbox" }).click();
    await expect(page.getByRole("heading", { name: "File Inbox", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Outbox" }).click();
    await expect(page.getByRole("heading", { name: "File Outbox", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Archive" }).click();
    await expect(page.getByRole("heading", { name: "Archived Files", level: 2 })).toBeVisible();
  });
});
