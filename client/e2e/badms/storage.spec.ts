import { expect, signedInAs, test } from "../support/test";

test.describe("badms: storage extension requests", () => {
  test.use(signedInAs("student"));

  test("student views storage extension requests interface", async ({ page }) => {
    await page.goto("/badms/storage-extensions");
    await expect(page.getByRole("heading", { name: "Storage Extension Requests" })).toBeVisible();
    await expect(page.getByText("Request quota extensions for departmental backup storage capacity")).toBeVisible();
  });
});
