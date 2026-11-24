import { expect, signedInAs, test, uniqueName } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, openDept, pageAs } from "./helpers";

test.describe("department: feedback", () => {
  test.use(signedInAs("deptStudent"));

  test("UC-DEPT-007/008/014: a student submits, Dept_Admin reviews, the HOD resolves", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    const subject = uniqueName("E2E feedback");

    await openDept(page, "deptStudent", "Feedback", "Feedback");
    await page.getByRole("button", { name: "Submit feedback" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Subject" }).fill(subject);
    await dialog.getByRole("textbox", { name: "Feedback" }).fill("The projector in L-104 flickers.");
    await dialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(subject)).toBeVisible();

    const admin = await pageAs(browser, "deptAdmin");
    await openDept(admin, "deptAdmin", "Feedback", "Feedback");
    const adminCard = admin.locator("div").filter({ hasText: subject })
      .filter({ has: admin.getByRole("button", { name: "Review" }) }).last();
    await adminCard.getByRole("button", { name: "Review" }).click();
    await admin.getByRole("dialog").getByRole("button", { name: "Save" }).click();
    await expect(admin.getByRole("dialog")).toBeHidden();
    await admin.context().close();

    const hod = await pageAs(browser, "deptHod");
    await openDept(hod, "deptHod", "Feedback", "Feedback");
    const hodCard = hod.locator("div").filter({ hasText: subject })
      .filter({ has: hod.getByRole("button", { name: "Resolve or close" }) }).last();
    await hodCard.getByRole("button", { name: "Resolve or close" }).click();
    const resolve = hod.getByRole("dialog");
    await resolve.getByRole("textbox", { name: "Note to the submitter" }).fill("Replaced the projector.");
    await resolve.getByRole("button", { name: "Save" }).click();
    await expect(resolve).toBeHidden();
    await hod.context().close();

    await page.reload();
    const mine = page.locator("div").filter({ has: page.getByText(subject, { exact: true }) })
      .filter({ hasText: "Outcome: Replaced the projector." });
    await expect(mine.last()).toBeVisible();
  });
});
