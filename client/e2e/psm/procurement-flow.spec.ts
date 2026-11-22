// End-to-end Playwright workflow for PSM vendor onboarding and dashboard navigation.
import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("psm: procurement operations", () => {
  test.use(signedInAs("psAdmin"));

  test("ps_admin opens dashboard and onboards a vendor (PSM-UC-019, PSM-UC-030)", async ({ page }) => {
    const vendorName = uniqueName("E2E Vendor");

    await page.goto("/");
    await actAs(page, "psAdmin");
    await openModuleNav(page, "Procurement & Stores");
    await sidebar(page).getByRole("link", { name: "Vendors" }).click();
    await expect(page.getByRole("heading", { name: "Vendors", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Onboard vendor" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Vendor name").fill(vendorName);
    await dialog.getByLabel("GSTIN").fill("23ABCDE1234F1Z5");
    await dialog.getByLabel("Bank account number").fill("123456789012");
    await dialog.getByLabel("Bank IFSC").fill("SBIN0001234");
    await dialog.getByLabel("Bank name").fill("SBI");
    await dialog.getByLabel("Compliance document reference").fill("gst.pdf");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/psm/vendors") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Save vendor" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: vendorName });
    await expect(row).toBeVisible();
  });
});
