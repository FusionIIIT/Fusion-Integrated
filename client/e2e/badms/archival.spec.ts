import { expect, signedInAs, test } from "../support/test";

test.describe("badms: archival requests", () => {
  test.use(signedInAs("student"));

  test("student accesses archival requests page and inspects interface", async ({ page }) => {
    await page.goto("/badms/archival-requests");
    await expect(page.getByRole("heading", { name: "Secure Archival Requests" })).toBeVisible();
    await expect(page.getByText("Submit and track structured departmental dataset archival")).toBeVisible();
  });
});
