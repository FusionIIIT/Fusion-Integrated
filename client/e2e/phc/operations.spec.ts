import { expect, signedInAs, test, uniqueName } from "../support/test";
import { choose, openPhc, waitForWrite } from "./support";

// PHC-UC-11 (ambulance), PHC-UC-12 (advisory reaches patients), PHC-UC-13 (report).
test.describe("phc: ambulance, advisories and reports", () => {
  test.use(signedInAs("phcStaff"));

  test("PHC staff log an ambulance run", async ({ page }) => {
    const destination = uniqueName("E2E District Hospital");
    await openPhc(page, "phcStaff", "Ambulance Log", "Ambulance log");
    await page.getByRole("button", { name: "Log ambulance use" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Date and time").fill("2026-01-15T08:40");
    await dialog.getByRole("textbox", { name: "Patient name" }).fill("E2E patient");
    await dialog.getByRole("textbox", { name: "Destination" }).fill(destination);
    const logged = waitForWrite(page, "ambulance");
    await dialog.getByRole("button", { name: "Save" }).click();
    expect((await logged).status()).toBe(201);
    await expect(page.getByRole("row").filter({ hasText: destination })).toBeVisible();
  });

  test("an advisory PHC staff publish reaches a student", async ({ page, browser }) => {
    const title = uniqueName("E2E heat advisory");
    await openPhc(page, "phcStaff", "Health Advisories", "Health advisories");
    await page.getByRole("button", { name: "Publish advisory" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Title" }).fill(title);
    await dialog.getByRole("textbox", { name: "Advisory" }).fill("Drink water.");
    const published = waitForWrite(page, "advisories");
    await dialog.getByRole("button", { name: "Publish" }).click();
    expect((await published).status()).toBe(201);

    const student = await browser.newContext(signedInAs("student"));
    const patient = await student.newPage();
    await openPhc(patient, "student", "Health Advisories", "Health advisories");
    await expect(patient.getByText(title)).toBeVisible();
    await expect(patient.getByRole("button", { name: "Publish advisory" })).toHaveCount(0);
    await student.close();
  });

  test("PHC staff generate an anonymised utilization report", async ({ page }) => {
    await openPhc(page, "phcStaff", "Reports", "Reports");
    await choose(page, "Report", "Service utilization");
    await page.getByLabel("From").fill("2026-01-01");
    await page.getByLabel("To").fill("2026-12-31");
    const report = page.waitForResponse((r) => r.url().includes("/api/v1/phc/reports"));
    await page.getByRole("button", { name: "Generate" }).click();
    expect((await report).status()).toBe(200);
    await expect(page.getByText(/Service utilization: 2026-01-01 to 2026-12-31/)).toBeVisible();
  });
});
