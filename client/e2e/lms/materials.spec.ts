import { expect, signedInAs, test, uniqueName } from "../support/test";

test.describe("lms: course materials", () => {
  test.use(signedInAs("student"));

  test("a student can navigate to /lms/materials", async ({ page }) => {
    await page.goto("/lms/materials");
    await expect(page.getByRole("heading", { name: "Course Materials" })).toBeVisible();
    await expect(page.getByRole("button", { name: /add material/i })).toHaveCount(0);
  });
});

test.describe("lms: faculty course materials", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member adds a lecture note visible on the materials page", async ({ page }) => {
    const title = uniqueName("Lecture Note");
    await page.goto("/lms/materials");
    await expect(page.getByRole("heading", { name: "Course Materials" })).toBeVisible();

    const addBtn = page.getByRole("button", { name: /add material/i });
    await expect(addBtn).toBeVisible();
    await addBtn.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByLabel(/^Title/i).fill(title);
    await dialog.getByLabel(/content text/i).fill("Comprehensive lecture notes on distributed systems.");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/lms/materials") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Publish Material" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    await expect(page.getByText(title)).toBeVisible();
  });
});
