import { expect, test, uniqueName } from "../support/test";
import {
  act, choose, ensureOffice, go, hasStatus, LONG, modal, NAMES, openApp, seat, submit, submitNew,
} from "./flow";

// One application from draft to a renewed patent, each use case its own step, through the UI.
const TITLE = uniqueName("E2E Graphene anode");
const RUN = TITLE.split(" ").pop() ?? "";

test.describe.serial("pms: from draft to a renewed patent", () => {
  test.beforeAll(async () => {
    await ensureOffice();
  });

  // UC-PMS-001 UC-PMS-003 UC-PMS-019 PMS-CFR-001
  test("an applicant drafts, names inventors, uploads the specification and submits", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant");
    const drawer = await submitNew(page, TITLE);
    await drawer.getByRole("tab", { name: "Inventors" }).click();
    await expect(drawer.getByRole("cell", { name: "AGR-E2E-1" })).toBeVisible();
    await drawer.getByRole("tab", { name: "Documents" }).click();
    await expect(drawer.getByText("Complete specification")).toBeVisible();
    await close();
  });

  // UC-PMS-002 PMS-CFR-012
  test("the applicant follows its status and history", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant");
    await go(page, "pmsApplicant", "My Applications");
    const row = page.getByRole("row").filter({ hasText: TITLE });
    await expect(row).toContainText(/submitted/i);
    const drawer = await openApp(page, TITLE);
    await drawer.getByRole("tab", { name: "History" }).click();
    await expect(drawer.getByText(/→ Submitted/i).first()).toBeVisible();
    await expect(drawer.getByRole("button", { name: "Edit details" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-007 PMS-CFR-020
  test("PCC_ADMIN assigns an unconflicted Director", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Oversight");
    await page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    const drawer = await openApp(page, TITLE);
    await act(page, drawer, "Assign Director");
    await choose(page, modal(page), "Director", new RegExp(NAMES.pmsDirector));
    await submit(page, "Assign", /\/assign-director$/);
    await hasStatus(drawer, "under review");
    await close();
  });

  // UC-PMS-008 PMS-CFR-024
  test("the Director approves it with a justification", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsDirector");
    await go(page, "pmsDirector", "Reviews");
    const drawer = await openApp(page, TITLE);
    await drawer.getByRole("tab", { name: "Documents" }).click();
    await expect(drawer.getByText("Complete specification")).toBeVisible();
    await act(page, drawer, "Record decision");
    await choose(page, modal(page), "Decision", "Approve");
    await modal(page).getByRole("textbox", { name: /Justification/ }).fill(LONG);
    await submit(page, "Record decision", /\/review$/);
    await hasStatus(drawer, "approved");
    await close();
  });

  // UC-PMS-010 UC-PMS-011 PMS-CFR-030
  test("PCC_ADMIN offers the case to a panel attorney, who accepts", async ({ browser }) => {
    const pcc = await seat(browser, "pmsPcc");
    await go(pcc.page, "pmsPcc", "Oversight");
    await pcc.page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    let drawer = await openApp(pcc.page, TITLE);
    await act(pcc.page, drawer, "Assign attorney");
    await choose(pcc.page, modal(pcc.page), "Panel attorney", new RegExp(NAMES.pmsAttorney));
    await submit(pcc.page, "Offer", /\/assign-attorney$/);
    await pcc.close();

    const { page, close } = await seat(browser, "pmsAttorney");
    await go(page, "pmsAttorney", "Assigned Cases");
    drawer = await openApp(page, TITLE);
    await act(page, drawer, "Accept case");
    await submit(page, "Accept", /\/respond$/);
    await hasStatus(drawer, "attorney assigned");
    await close();
  });

  // UC-PMS-012 UC-PMS-033 PMS-CFR-035
  test("the attorney records and finalizes an opinion and records advice", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsAttorney");
    await go(page, "pmsAttorney", "Assigned Cases");
    const drawer = await openApp(page, TITLE);
    await act(page, drawer, "Record opinion");
    for (const field of ["Analysis", "Novelty", "Non obviousness", "Utility"]) {
      await modal(page).getByRole("textbox", { name: field }).fill(LONG);
    }
    await choose(page, modal(page), "Recommendation", "File patent");
    await submit(page, "Save draft", /\/assessments$/);
    await act(page, drawer, "Finalize opinion");
    await submit(page, "Finalize", /\/finalize$/);
    await act(page, drawer, "Record advice");
    await modal(page).getByRole("textbox", { name: "Advice" }).fill("File in India first.");
    await submit(page, "Record", /\/legal-advice$/);
    await expect(drawer.getByRole("button", { name: "Finalize opinion" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-009 PMS-CFR-040
  test("the attorney proposes a budget and the Director approves it", async ({ browser }) => {
    const attorney = await seat(browser, "pmsAttorney");
    await go(attorney.page, "pmsAttorney", "Assigned Cases");
    let drawer = await openApp(attorney.page, TITLE);
    await act(attorney.page, drawer, "Propose budget");
    await modal(attorney.page).getByRole("textbox", { name: "Filing fees (Rs)" }).fill("8000");
    await modal(attorney.page).getByRole("textbox", { name: "Attorney fees (Rs)" }).fill("20000");
    await modal(attorney.page).getByRole("textbox", { name: "Administrative costs (Rs)" }).fill("2000");
    await submit(attorney.page, "Propose", /\/budgets$/, 201);
    await attorney.close();

    const { page, close } = await seat(browser, "pmsDirector");
    await go(page, "pmsDirector", "Reviews");
    drawer = await openApp(page, TITLE);
    await act(page, drawer, "Decide budget");
    await choose(page, modal(page), "Decision", "Approve");
    await submit(page, "Record", /\/decision$/);
    await expect(drawer.getByRole("button", { name: "Decide budget" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-013 UC-PMS-014 UC-PMS-015 UC-PMS-029 PMS-CFR-045
  test("the attorney files, an office action is answered with the applicant's approval, and it is granted", async ({ browser }) => {
    const attorney = await seat(browser, "pmsAttorney");
    await go(attorney.page, "pmsAttorney", "Assigned Cases");
    let drawer = await openApp(attorney.page, TITLE);
    await act(attorney.page, drawer, "Record filing");
    await modal(attorney.page).getByRole("textbox", { name: "Application number" }).fill(`IN-${RUN}`);
    await modal(attorney.page).getByRole("textbox", { name: "Confirmation" }).fill("ACK-1");
    await submit(attorney.page, "Record filing", /\/filings$/);
    await hasStatus(drawer, "filed");
    await act(attorney.page, drawer, "Record communication");
    await choose(attorney.page, modal(attorney.page), "Kind", "Office action");
    await modal(attorney.page).getByRole("textbox", { name: "Reference" }).fill("FER-1");
    await modal(attorney.page).getByRole("checkbox", { name: "Applicant must approve the response" }).check();
    await submit(attorney.page, "Record", /\/communications$/);
    await act(attorney.page, drawer, "Draft response FER-1");
    await modal(attorney.page).getByRole("textbox", { name: "Response" }).fill("Claim 1 amended.");
    await submit(attorney.page, "Save response", /\/response$/);
    await attorney.close();

    const applicant = await seat(browser, "pmsApplicant");
    await go(applicant.page, "pmsApplicant", "My Applications");
    drawer = await openApp(applicant.page, TITLE);
    await act(applicant.page, drawer, "Approve response FER-1");
    await submit(applicant.page, "Approve", /\/approve$/);
    await applicant.close();

    const { page, close } = await seat(browser, "pmsAttorney");
    await go(page, "pmsAttorney", "Assigned Cases");
    drawer = await openApp(page, TITLE);
    await act(page, drawer, "Record submission FER-1");
    await modal(page).getByRole("textbox", { name: "Submission reference" }).fill("SUB-1");
    await submit(page, "Record", /\/submission$/);
    await act(page, drawer, "Record communication");
    await choose(page, modal(page), "Kind", "Grant");
    await modal(page).getByRole("textbox", { name: "Reference" }).fill("GRANT-1");
    await modal(page).getByRole("textbox", { name: "Grant date (grants)" }).fill("2026-11-21");
    await modal(page).getByRole("textbox", { name: "Patent number (grants)" }).fill(`IN-PAT-${RUN}`);
    await modal(page).getByRole("textbox", { name: "Granted in (grants)" }).fill("IN");
    await submit(page, "Record", /\/communications$/);
    await hasStatus(drawer, "granted");
    await close();
  });

  // UC-PMS-017 UC-PMS-018 PMS-CFR-055
  test("a maintenance fee is put to the Director, approved and paid", async ({ browser }) => {
    const attorney = await seat(browser, "pmsAttorney");
    await go(attorney.page, "pmsAttorney", "Assigned Cases");
    let drawer = await openApp(attorney.page, TITLE);
    await act(attorney.page, drawer, "Add maintenance due date");
    await modal(attorney.page).getByRole("textbox", { name: "Due on" }).fill("2027-11-21");
    await submit(attorney.page, "Add", /\/maintenance-cycles$/);
    await act(attorney.page, drawer, "Ask for renewal decision");
    await submit(attorney.page, "Ask the Director", /\/request-decision$/);
    await attorney.close();

    const director = await seat(browser, "pmsDirector");
    await go(director.page, "pmsDirector", "Reviews");
    drawer = await openApp(director.page, TITLE);
    await act(director.page, drawer, "Decide renewal");
    await choose(director.page, modal(director.page), "Decision", "Renew");
    await submit(director.page, "Record", /\/decision$/);
    await director.close();

    const { page, close } = await seat(browser, "pmsAttorney");
    await go(page, "pmsAttorney", "Assigned Cases");
    drawer = await openApp(page, TITLE);
    await act(page, drawer, "Record maintenance payment");
    await modal(page).getByRole("textbox", { name: "Receipt reference" }).fill("RCPT-1");
    await modal(page).getByRole("textbox", { name: "Amount (Rs)" }).fill("4000");
    await submit(page, "Record", /\/action$/);
    await expect(drawer.getByRole("button", { name: "Record maintenance payment" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-020 UC-PMS-021 BR-PMS-088
  test("the applicant asks to license the patent; it is routed and PCC_ADMIN records the deal", async ({ browser }) => {
    const applicant = await seat(browser, "pmsApplicant");
    await go(applicant.page, "pmsApplicant", "Licensing");
    await applicant.page.getByRole("button", { name: "New request" }).click();
    await choose(applicant.page, modal(applicant.page), "Application", new RegExp(TITLE));
    await choose(applicant.page, modal(applicant.page), "Kind", "Licensing");
    await modal(applicant.page).getByRole("textbox", { name: /What you want/ })
      .fill(`License ${TITLE} to a battery maker.`);
    await submit(applicant.page, "Submit", /\/licensing-requests$/, 201);
    const mine = applicant.page.getByRole("row").filter({ hasText: TITLE });
    await expect(mine).toContainText("Technology Transfer Committee");
    await expect(mine.getByRole("button")).toHaveCount(0);
    await applicant.close();

    const { page, close } = await seat(browser, "pmsPcc");
    await go(page, "pmsPcc", "Licensing");
    const row = page.getByRole("row").filter({ hasText: TITLE });
    await expect(row).toContainText(/routed/i);
    await row.getByRole("button", { name: "Add note" }).click();
    await modal(page).getByRole("textbox", { name: "Note" }).fill("Term sheet received.");
    await submit(page, "Add", /\/notes$/);
    await expect(row).toContainText(/negotiating/i);
    await row.getByRole("button", { name: "Record agreement" }).click();
    await modal(page).getByRole("textbox", { name: "Other party" }).fill("Cell Co");
    await modal(page).getByRole("textbox", { name: "Terms", exact: true }).fill("Exclusive in India, five years.");
    await submit(page, "Record", /\/agreement$/);
    await expect(row.getByRole("button")).toHaveCount(0);
    await close();
  });
});
