import { expect, test, uniqueName } from "../support/test";
import {
  act, assignDirector, choose, decide, ensureOffice, go, hasStatus, LONG, modal, NAMES, openApp,
  seat, submit, submitNew,
} from "./flow";

const TITLE = uniqueName("E2E Revised sensor");
const ANSWER = "Claim 1 now names the sensing layer and its thickness, as the Director asked.";

test.describe.serial("pms: revision, rejection and appeal", () => {
  test.beforeAll(async () => {
    await ensureOffice();
  });

  test("an application is submitted and sent back for revision", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant2");
    await submitNew(page, TITLE, "pmsApplicant2");
    await close();
    await assignDirector(browser, TITLE, "pmsDirector");
    await decide(browser, TITLE, "pmsDirector", "Needs revision");
  });

  // UC-PMS-005 PMS-CFR-026
  test("the applicant answers every piece of feedback and resubmits", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant2");
    await go(page, "pmsApplicant2", "My Applications");
    const drawer = await openApp(page, TITLE);
    await hasStatus(drawer, "needs revision");
    await expect(drawer.getByText(LONG).first()).toBeVisible();
    await act(page, drawer, "Edit details");
    await modal(page).getByRole("textbox", { name: "Claims" })
      .fill("1. A humidity sensor with a 40 nm graphene oxide sensing layer.");
    await submit(page, "Save", /\/pms\/applications\/\d+$/);
    await act(page, drawer, "Resubmit");
    const answers = modal(page).getByRole("textbox", { name: /How you addressed/ });
    for (const box of await answers.all()) await box.fill(ANSWER);
    await submit(page, "Resubmit", /\/resubmit$/);
    await hasStatus(drawer, "resubmitted");
    await close();
  });

  // UC-PMS-022 PMS-CFR-070
  test("the resubmission is rejected and the applicant appeals in time", async ({ browser }) => {
    await assignDirector(browser, TITLE, "pmsDirector");
    await decide(browser, TITLE, "pmsDirector", "Reject");
    const { page, close } = await seat(browser, "pmsApplicant2");
    await go(page, "pmsApplicant2", "My Applications");
    const drawer = await openApp(page, TITLE);
    await hasStatus(drawer, "rejected");
    await act(page, drawer, "Appeal");
    await modal(page).getByRole("textbox", { name: "Grounds" }).fill("The prior art cited is unrelated.");
    await modal(page).getByRole("textbox", { name: "Justification" }).fill(ANSWER);
    await submit(page, "File appeal", /\/appeal$/);
    await expect(drawer.getByRole("button", { name: "Appeal" })).toHaveCount(0);
    await close();
  });

  // UC-PMS-023 BR-PMS-071
  test("PCC_ADMIN gives the appeal to a different Director, who remands it", async ({ browser }) => {
    const pcc = await seat(browser, "pmsPcc");
    await go(pcc.page, "pmsPcc", "Oversight");
    await pcc.page.getByRole("textbox", { name: "Search by title or reference" }).fill(TITLE);
    let drawer = await openApp(pcc.page, TITLE);
    await act(pcc.page, drawer, "Assign appeal Director");
    await modal(pcc.page).getByRole("textbox", { name: "Director" }).click();
    await expect(pcc.page.getByRole("option", { name: new RegExp(NAMES.pmsDirector) })).toHaveCount(0);
    await pcc.page.getByRole("option", { name: new RegExp(NAMES.pmsDirector2) }).click();
    await submit(pcc.page, "Assign", /\/appeals\/\d+\/assign$/);
    await pcc.close();

    const { page, close } = await seat(browser, "pmsDirector2");
    await go(page, "pmsDirector2", "Reviews");
    drawer = await openApp(page, TITLE);
    await act(page, drawer, "Decide appeal");
    await choose(page, modal(page), "Outcome", "Remand for Amendment");
    await modal(page).getByRole("textbox", { name: /Justification/ }).fill(LONG);
    await submit(page, "Record outcome", /\/decision$/);
    await hasStatus(drawer, "needs revision");
    await close();
  });

  // UC-PMS-004 PMS-CFR-015
  test("the applicant records prior art and finds it again by search", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant2");
    await go(page, "pmsApplicant2", "Prior Art Search");
    await page.getByRole("button", { name: "Attach a reference" }).click();
    await choose(page, modal(page), "Application", new RegExp(TITLE));
    await choose(page, modal(page), "Kind", "Publication");
    await modal(page).getByRole("textbox", { name: "Title", exact: true })
      .fill(`Thin-film humidity sensing ${TITLE}`);
    await modal(page).getByRole("textbox", { name: "Patent number or DOI" }).fill("10.1000/e2e");
    await submit(page, "Attach", /\/prior-art$/, 201);
    await page.getByRole("textbox", { name: "Search terms" }).fill("humidity sensing");
    const searched = page.waitForResponse((r) => r.url().endsWith("/prior-art/searches"));
    await page.getByRole("button", { name: "Search" }).click();
    expect((await searched).status()).toBe(200);
    await expect(page.getByText(`Thin-film humidity sensing ${TITLE}`)).toBeVisible();
    await expect(page.getByText(/not connected/).first()).toBeVisible();
    await close();
  });
});

test.describe.serial("pms: withdrawal", () => {
  const OTHER = uniqueName("E2E Withdrawn idea");

  test.beforeAll(async () => {
    await ensureOffice();
  });

  // UC-PMS-006 PMS-CFR-018
  test("the applicant withdraws a submitted application, which then cannot be acted on", async ({ browser }) => {
    const { page, close } = await seat(browser, "pmsApplicant2");
    const drawer = await submitNew(page, OTHER, "pmsApplicant2");
    await act(page, drawer, "Withdraw");
    await modal(page).getByRole("textbox", { name: "Reason" }).fill("We will publish instead.");
    await submit(page, "Withdraw", /\/withdraw$/);
    await hasStatus(drawer, "withdrawn");
    await expect(drawer.getByRole("button", { name: "Withdraw" })).toHaveCount(0);
    await close();

    const pcc = await seat(browser, "pmsPcc");
    await go(pcc.page, "pmsPcc", "Oversight");
    await pcc.page.getByRole("textbox", { name: "Search by title or reference" }).fill(OTHER);
    const seen = await openApp(pcc.page, OTHER);
    await expect(seen.getByRole("button", { name: "Assign Director" })).toHaveCount(0);
    await pcc.close();
  });
});
