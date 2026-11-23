import { ACCOUNTS } from "../accounts";
import { expect, signedInAs, test, uniqueName } from "../support/test";
import { choose, openPhc, waitForWrite } from "./support";

// PHC-UC-06 (record), PHC-UC-02 and PHC-UC-03 (patient reads and downloads), PHC-UC-04 (claim),
// PHC-UC-15, 19, 20, 21 (each office moves it), PHC-UC-05 (claimant tracks it).
test.describe("phc: records and reimbursement", () => {
  test.use(signedInAs("phcStaff"));

  test("a visit is recorded, then claimed for and carried to reimbursed", async ({
    page, browser,
  }) => {
    const complaint = uniqueName("E2E fever");
    await openPhc(page, "phcStaff", "Medical Records", "Medical records");
    await page.getByRole("button", { name: "Record visit" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Search patient by name" })
      .fill(ACCOUNTS.phcEmployee.username);
    await choose(page, "Patient", /\(faculty\)/);
    await dialog.getByRole("textbox", { name: "Complaint" }).fill(complaint);
    await dialog.getByRole("textbox", { name: "Medicine 1" }).fill("Paracetamol 500mg");
    await dialog.getByRole("textbox", { name: "Dosage" }).fill("1-0-1");
    const recorded = waitForWrite(page, "records");
    await dialog.getByRole("button", { name: "Save visit" }).click();
    expect((await recorded).status()).toBe(201);

    const employeeCtx = await browser.newContext(signedInAs("phcEmployee"));
    const employee = await employeeCtx.newPage();
    await openPhc(employee, "phcEmployee", "Medical Records", "Medical records");
    const visit = employee.locator(".mantine-Card-root").filter({ hasText: complaint });
    await expect(visit).toContainText("Paracetamol 500mg");
    await expect(employee.getByRole("button", { name: "Record visit" })).toHaveCount(0);
    await visit.getByRole("checkbox").check();
    const download = employee.waitForEvent("download");
    await employee.getByRole("button", { name: "Download PDF" }).click();
    expect((await download).suggestedFilename()).toMatch(/\.pdf$/);

    await openPhc(employee, "phcEmployee", "Reimbursements", "Medical bill reimbursement");
    await employee.getByRole("button", { name: "New claim" }).click();
    await choose(employee, "Prescription", /Paracetamol 500mg/);
    const today = new Date().toISOString().slice(0, 10);
    const form = employee.getByRole("dialog");
    await form.getByLabel("Medical expense date").fill(today);
    await form.getByRole("textbox", { name: "Amount (₹)" }).fill("450");
    await form.getByRole("textbox", { name: "Description" }).fill(complaint);
    const submitted = waitForWrite(employee, "claims");
    await form.getByRole("button", { name: "Submit claim" }).click();
    const claim = await (await submitted).json() as { id: number };
    await expect(employee.getByText(`Claim #${claim.id}`)).toBeVisible();

    const steps = [
      ["phcStaff", "Forward to Accounts"],
      ["phcAccounts", "Mark verified"],
      ["phcAuthority", "Approve sanction"],
      ["phcAccounts", "Record payment"],
    ] as const;
    for (const [role, button] of steps) {
      await openPhc(page, role, "Reimbursements", "Medical bill reimbursement");
      const row = page.locator(".mantine-Card-root").filter({ hasText: `Claim #${claim.id}` });
      const moved = waitForWrite(page, `claims/${claim.id}/transition`);
      await row.getByRole("button", { name: button }).click();
      expect((await moved).status()).toBe(200);
    }

    await openPhc(employee, "phcEmployee", "Reimbursements", "Medical bill reimbursement");
    const mine = employee.locator(".mantine-Card-root").filter({ hasText: `Claim #${claim.id}` });
    await expect(mine).toContainText("Reimbursed");
    await expect(mine).toContainText("pay");
    await employeeCtx.close();
  });
});
