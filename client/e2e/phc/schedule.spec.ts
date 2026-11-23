import { expect, signedInAs, test, uniqueName } from "../support/test";
import { openPhc, waitForWrite } from "./support";

// PHC-UC-22, PHC-UC-07, PHC-UC-08, then PHC-UC-01 for the patient.
test.describe("phc: doctor schedule", () => {
  test.use(signedInAs("phcStaff"));

  test("PHC staff create, edit, publish and mark a schedule; a patient sees it", async ({
    page, browser,
  }) => {
    const doctor = uniqueName("Dr E2E");
    await openPhc(page, "phcStaff", "Doctor Schedule", "Doctor schedule");

    await page.getByRole("button", { name: "New schedule" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Doctor name" }).fill(doctor);
    await dialog.getByRole("textbox", { name: "From", exact: true }).fill("09:00");
    await dialog.getByRole("textbox", { name: "To", exact: true }).fill("11:00");
    const created = waitForWrite(page, "schedules");
    await dialog.getByRole("button", { name: "Save" }).click();
    expect((await created).status()).toBe(201);

    const card = page.locator(".mantine-Card-root").filter({ hasText: doctor });
    await card.getByRole("button", { name: "Edit" }).click();
    await page.getByRole("dialog").getByRole("textbox", { name: "To", exact: true })
      .fill("12:00");
    const edited = waitForWrite(page, "schedules/");
    await page.getByRole("dialog").getByRole("button", { name: "Save" }).click();
    expect((await edited).status()).toBe(200);
    await expect(card).toContainText("09:00–12:00");

    const published = waitForWrite(page, "schedules/");
    await card.getByRole("button", { name: "Publish" }).click();
    expect((await published).status()).toBe(200);
    const marked = waitForWrite(page, "schedules/");
    await card.getByRole("button", { name: "Mark available" }).click();
    expect((await marked).status()).toBe(200);

    const student = await browser.newContext(signedInAs("student"));
    const patient = await student.newPage();
    await openPhc(patient, "student", "Doctor Schedule", "Doctor schedule");
    const seen = patient.locator(".mantine-Card-root").filter({ hasText: doctor });
    await expect(seen).toContainText("Available");
    await expect(seen.getByRole("button")).toHaveCount(0);
    await student.close();
  });
});
