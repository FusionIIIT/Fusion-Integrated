import { expect, signedInAs, test, uniqueName, actAs, openModuleNav } from "../support/test";
import {
  clickAndExpectOk, closeDrawer, DEPARTMENT, enter, finish, MODULE_LABEL, openItem, openPage,
  rowFor,
} from "./actors";
import { configureIaa } from "./setup";

// IAA-UC-101, 102, 103, 105 and 201; workflow BW-IAA-01: draft, submit, validate, approve, record.
test.describe("iaa: an expense request, from draft to recorded", () => {
  test.use(signedInAs("iaaFaculty"));
  test.beforeAll(async () => { await configureIaa(); });

  test("an employee submits it, Finance validates, the HoD approves, Finance records it",
    async ({ page, browser }) => {
      const title = uniqueName("E2E Lab kits");

      // The employee drafts it, attaches a document and submits it.
      await page.goto("/");
      await actAs(page, "iaaFaculty");
      await openModuleNav(page, MODULE_LABEL);
      await openPage(page, "My Requests & TA", "My requests & TA claims");
      await page.getByRole("button", { name: "New", exact: true }).click();
      const form = page.getByRole("dialog");
      await form.getByRole("textbox", { name: "Department" }).fill(DEPARTMENT);
      await form.getByRole("textbox", { name: "Amount (₹)" }).fill("12000");
      await form.getByRole("textbox", { name: "Request type" }).fill("voucher");
      await form.getByRole("textbox", { name: "Title" }).fill(title);
      await form.getByRole("textbox", { name: "What is it for?" }).fill("Soldering kits");
      await clickAndExpectOk(page, /\/api\/v1\/iaa\/records$/,
        () => form.getByRole("button", { name: "Save draft" }).click());

      // Saving opens the item's drawer.
      await expect(page.getByText("New expense / voucher request")).toBeHidden();
      await page.getByRole("textbox", { name: "Document title" }).fill("Invoice");
      await page.getByRole("textbox", { name: "https:// link" })
        .fill("https://files.example.com/invoice.pdf");
      await clickAndExpectOk(page, /\/records\/\d+\/documents$/,
        () => page.getByRole("button", { name: "Attach" }).click());
      await clickAndExpectOk(page, /\/records\/\d+\/submit$/,
        () => page.getByRole("button", { name: "Submit to Finance" }).click());
      await closeDrawer(page);
      await expect(rowFor(page, title)).toContainText(/submitted|finance/i);

      // Finance validates it.
      const finance = await enter(browser, "iaaFinance");
      await openPage(finance.page, "Finance Review", "Finance review");
      await openItem(finance.page, title);
      await clickAndExpectOk(finance.page, /\/records\/\d+\/validate$/,
        () => finance.page.getByRole("button", { name: "Validate request" }).click());
      await closeDrawer(finance.page);

      // The HoD of the department approves it, with remarks.
      const hod = await enter(browser, "iaaHod");
      await openPage(hod.page, "Approvals", "Approvals");
      await openItem(hod.page, title);
      await hod.page.getByRole("textbox", { name: "Remarks (required)" }).fill("Within plan");
      await clickAndExpectOk(hod.page, /\/records\/\d+\/decision$/,
        () => hod.page.getByRole("button", { name: "Record decision" }).click());
      await closeDrawer(hod.page);

      // Finance records it. Recording moves no money.
      await finance.page.reload();
      await openPage(finance.page, "Finance Review", "Finance review");
      await finance.page.getByText("To record").click();
      await openItem(finance.page, title);
      await expect(finance.page.getByText(/No payment is made/)).toBeVisible();
      await finance.page.getByRole("textbox", { name: "Processing reference" }).fill("VCH-E2E");
      await clickAndExpectOk(finance.page, /\/records\/\d+\/processing$/,
        () => finance.page.getByRole("button", { name: "Record processing" }).click());
      await finish(finance, hod);

      // The employee sees it recorded; nothing is left to submit.
      await page.reload();
      await openPage(page, "My Requests & TA", "My requests & TA claims");
      await expect(rowFor(page, title)).toContainText(/recorded|processed/i);
      await openItem(page, title);
      await expect(page.getByRole("button", { name: "Submit to Finance" })).toHaveCount(0);
    });
});
