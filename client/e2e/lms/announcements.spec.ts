import { expect, signedInAs, test, uniqueName } from "../support/test";

test.describe("lms: course announcements", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/announcements", async ({ page }) => {
    await page.goto("/lms/announcements");
    await expect(page.getByRole("heading", { name: "Announcements" })).toBeVisible();
    await expect(page.getByRole("button", { name: /new announcement/i })).toHaveCount(0);
  });
});

test.describe("lms: faculty course announcements", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member posts an announcement visible on the course feed", async ({ page }) => {
    const title = uniqueName("Announcement");
    await page.goto("/lms/announcements");
    await expect(page.getByRole("heading", { name: "Announcements" })).toBeVisible();

    const newBtn = page.getByRole("button", { name: /new announcement/i });
    await expect(newBtn).toBeVisible();
    await newBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/announcement title/i).fill(title);
    await dialog.getByLabel(/content/i).fill("Detailed test announcement body for e2e.");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/lms/announcements") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Post Announcement" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    await expect(page.getByText(title)).toBeVisible();
  });
});
