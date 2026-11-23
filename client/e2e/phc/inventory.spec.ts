import { expect, signedInAs, test, uniqueName } from "../support/test";
import { choose, openPhc, waitForWrite } from "./support";

// PHC-UC-09 (stock and low-stock alert), PHC-UC-10 (requisition), PHC-UC-16 (decision),
// PHC-UC-14 (fulfilled).
test.describe("phc: inventory and requisitions", () => {
  test.use(signedInAs("phcStaff"));

  test("stock falls below threshold, a requisition is approved and fulfilled", async ({
    page, browser,
  }) => {
    const name = uniqueName("E2E ORS");
    await openPhc(page, "phcStaff", "Inventory", "Inventory");
    await page.getByRole("button", { name: "Add item" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Name" }).fill(name);
    await dialog.getByRole("textbox", { name: "Unit" }).fill("sachet");
    await dialog.getByRole("textbox", { name: "Opening stock" }).fill("20");
    await dialog.getByRole("textbox", { name: "Reorder threshold" }).fill("10");
    const created = waitForWrite(page, "inventory");
    await dialog.getByRole("button", { name: "Save" }).click();
    expect((await created).status()).toBe(201);

    const row = page.getByRole("row").filter({ hasText: name });
    await row.getByRole("button", { name: "Adjust stock" }).click();
    await page.getByRole("dialog").getByRole("textbox", { name: /quantity to add/i }).fill("-15");
    const adjusted = waitForWrite(page, "inventory/");
    await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
    expect((await adjusted).status()).toBe(201);
    await expect(page.getByText(`${name}: 5.00 left, threshold 10.00`)).toBeVisible();

    await openPhc(page, "phcStaff", "Requisitions", "Procurement requisitions");
    await page.getByRole("button", { name: "New requisition" }).click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: "Purpose" }).fill(name);
    await choose(page, "Item 1", new RegExp(name));
    await form.getByRole("textbox", { name: "Quantity" }).fill("100");
    const raised = waitForWrite(page, "requisitions");
    await form.getByRole("button", { name: "Submit" }).click();
    const req = await (await raised).json() as { id: number };

    const authorityCtx = await browser.newContext(signedInAs("phcRequisitionAuthority"));
    const authority = await authorityCtx.newPage();
    await openPhc(authority, "phcRequisitionAuthority", "Requisitions", "Procurement requisitions");
    const pending = authority.locator(".mantine-Card-root").filter({ hasText: `#${req.id}` });
    const decided = waitForWrite(authority, `requisitions/${req.id}/transition`);
    await pending.getByRole("button", { name: "Approve" }).click();
    expect((await decided).status()).toBe(200);
    await authorityCtx.close();

    await openPhc(page, "phcStaff", "Requisitions", "Procurement requisitions");
    const approved = page.locator(".mantine-Card-root").filter({ hasText: `#${req.id}` });
    const fulfilled = waitForWrite(page, `requisitions/${req.id}/transition`);
    await approved.getByRole("button", { name: "Mark fulfilled" }).click();
    expect((await fulfilled).status()).toBe(200);
    await expect(approved).toContainText("Fulfilled");

    await openPhc(page, "phcStaff", "Notifications", "Notifications");
    await expect(page.getByText(`Your requisition #${req.id} was approved.`)).toBeVisible();
  });
});
