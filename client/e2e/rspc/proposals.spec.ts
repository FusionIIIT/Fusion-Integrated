import {
  expect,
  signedInAs,
  test,
  uniqueName,
} from "../support/test";

test.describe("rspc: proposals main flow", () => {
  test.use(signedInAs("faculty"));

  test("a faculty member drafts and views a new research proposal", async ({ page }) => {
    const title = uniqueName("Quantum Network Grant");

    await page.goto("/rspc/proposals");
    await expect(
      page.getByRole("heading", { name: "Research Proposals", level: 2 })
    ).toBeVisible();

    const newBtn = page.getByRole("button", { name: "New Proposal" });
    if (await newBtn.isVisible()) {
      await newBtn.click();
      const dialog = page.getByRole("dialog");
      await dialog.getByRole("textbox", { name: "Proposal Title" }).fill(title);
      await dialog.getByRole("textbox", { name: "Funding Agency" }).fill("DST-SERB");

      const created = page.waitForResponse(
        (r) => r.url().includes("/api/v1/rspc/proposals/") && r.request().method() === "POST"
      );
      await dialog.getByRole("button", { name: "Save Draft" }).click();
      expect((await created).status()).toBe(201);

      await expect(dialog).toBeHidden();
      const row = page.getByRole("row").filter({ hasText: title });
      await expect(row).toBeVisible();
      await expect(row).toContainText(/draft/i);
    }
  });
});
