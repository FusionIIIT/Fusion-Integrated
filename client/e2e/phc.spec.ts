import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.use({ viewport: { width: 1920, height: 1080 }, acceptDownloads: true });

function session(permissions: string[]) {
  return {
    user: {
      id: 1,
      username: "doctor",
      display_name: "Dr. Test",
      kind: "employee",
      email: "doctor@example.test",
    },
    active_role: "employee",
    roles: ["employee"],
    permissions,
    modules: ["phc"],
    navigation: [{
      section: "PHC",
      items: [
        {
          code: "phc.schedule",
          label: "Doctor Schedule",
          icon: "Calendar",
          to: "/phc/schedule",
        },
        {
          code: "phc.records",
          label: "My Medical Records",
          icon: "FileText",
          to: "/phc/records",
        },
      ],
    }],
    csrf_token: "test-csrf",
  };
}

async function stubMe(page: import("@playwright/test").Page, permissions: string[]) {
  await page.route("**/api/v1/me", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(session(permissions)),
  }));
}

function trackErrors(page: import("@playwright/test").Page): string[] {
  const errors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  page.on("pageerror", (error) => errors.push(error.message));
  return errors;
}

const SCHEDULE = { schedules: [], attendance: {} };

test("PHC schedule loads, is accessible and is keyboard reachable", async ({ page }) => {
  const consoleErrors = trackErrors(page);
  await stubMe(page, ["phc.schedule.view"]);
  await page.route("**/api/v1/phc/schedule", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(SCHEDULE),
  }));

  await page.goto("/phc/schedule");

  await expect(page.getByRole("heading", { name: "Doctor Schedule" })).toBeVisible();
  await expect(page.getByText("No published schedule yet")).toBeVisible();

  await page.locator("body").click({ position: { x: 1, y: 1 } });
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Notifications" })).toBeFocused();

  const { violations } = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(violations).toEqual([]);
  expect(consoleErrors).toEqual([]);
});

test("PHC record drawer renders and downloads a real PDF", async ({ page }) => {
  const consoleErrors = trackErrors(page);
  await stubMe(page, ["phc.records.view_self"]);
  await page.route("**/api/v1/phc/records", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ results: [{
      id: 7, patient: 2001, recorded_by: 1002,
      visit_date: "2026-11-20T09:30:00Z", notes: "Annual check-up",
    }] }),
  }));
  await page.route("**/api/v1/phc/records/prescriptions", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ results: [{
      id: 3, visit: 7, patient: 2001, medicine: "Paracetamol",
      dosage: "500mg", recorded_by: 1002,
      created_at: "2026-11-20T09:35:00Z",
    }] }),
  }));
  await page.route("**/api/v1/phc/records/download/7", (route) => route.fulfill({
    status: 200,
    contentType: "application/pdf",
    headers: {
      "content-disposition": 'attachment; filename="phc-record-7.pdf"',
    },
    body: "%PDF-1.4\n1 0 obj <<>> endobj\n%%EOF\n",
  }));

  await page.goto("/phc/records");
  await expect(page.getByRole("heading", { name: "My Medical Records" })).toBeVisible();
  await page.getByRole("button", { name: "View" }).click();

  const drawer = page.getByRole("dialog");
  await expect(drawer.getByText("Annual check-up")).toBeVisible();
  await expect(drawer.getByText("Paracetamol")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download PDF" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("phc-record-7.pdf");
  expect(consoleErrors).toEqual([]);
});
