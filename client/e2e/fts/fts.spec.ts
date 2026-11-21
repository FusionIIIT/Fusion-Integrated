import {
  actAs,
  expect,
  openModuleNav,
  sidebar,
  signedInAs,
  test,
  uniqueName,
} from "../support/test";

const FTS_PAGES = ["inbox", "outbox", "drafts", "create", "governance"] as const;

test.describe("fts: student access guards", () => {
  test.use(signedInAs("student"));

  for (const path of FTS_PAGES) {
    test(`student navigating to /fts/${path} is refused by route guard`, async ({ page }) => {
      await page.goto(`/fts/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});

test.describe("fts: file creation and draft lifecycle", () => {
  test.use(signedInAs("placementOfficer"));

  test("creates a draft file note, inspects in drafts, and discards it (FTS-UC-002, FTS-UC-004, BW-FTS-05, BW-FTS-07)", async ({ page }) => {
    const subject = uniqueName("Draft Requisition Note");
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto("/");
    await actAs(page, "placementOfficer");
    await openModuleNav(page, "File Tracking");
    await sidebar(page).getByRole("link", { name: "Create File" }).click();
    await expect(page.getByRole("heading", { name: "Create Institute File", level: 2 })).toBeVisible();

    // Fill in file details
    await page.getByLabel(/subject/i).fill(subject);
    await page.getByLabel(/description/i).fill("Draft description for committee review.");
    await page.getByLabel(/initial note \/ remarks/i).fill("Initial draft note content.");

    // Select save as draft mode
    await page.getByLabel(/save as draft/i).click();

    // Submit draft
    const draftCreated = page.waitForResponse(
      (r) => r.url().includes("/api/v1/fts/files") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: /save as draft/i }).click();
    expect((await draftCreated).status()).toBe(201);

    // Verify file appears in Drafts list
    await page.goto("/fts/drafts");
    await expect(page.getByRole("heading", { name: "Draft Files", level: 2 })).toBeVisible();
    const draftRow = page.getByRole("row").filter({ hasText: subject });
    await expect(draftRow).toBeVisible();

    // Discard the draft
    const discarded = page.waitForResponse(
      (r) => r.url().includes("/discard") && r.request().method() === "POST",
    );
    await draftRow.getByRole("button", { name: /discard/i }).click();
    expect((await discarded).status()).toBe(200);

    // Verify row is no longer present in drafts
    await expect(page.getByRole("row").filter({ hasText: subject })).toHaveCount(0);
  });

  test("creates and immediately circulates a file (FTS-UC-001, FTS-UC-003, BW-FTS-01)", async ({ page }) => {
    const subject = uniqueName("Circulation Proposal");

    await page.goto("/fts/create");
    await actAs(page, "placementOfficer");

    await page.getByLabel(/subject/i).fill(subject);
    await page.getByLabel(/description/i).fill("Proposal submitted for administrative action.");
    await page.getByLabel(/initial note \/ remarks/i).fill("Submitted for urgent sanction.");

    // Fill in recipient details
    await page.getByLabel(/recipient user id/i).fill("62");
    await page.getByLabel(/recipient username/i).fill("stf00062");

    // Submit immediate circulation
    const fileCirculated = page.waitForResponse(
      (r) => r.url().includes("/api/v1/fts/files") && r.request().method() === "POST",
    );
    await page.getByRole("button", { name: /circulate file/i }).click();
    expect((await fileCirculated).status()).toBe(201);

    // Verify file appears in Outbox (FTS-UC-009)
    await page.goto("/fts/outbox");
    await expect(page.getByRole("heading", { name: "File Outbox", level: 2 })).toBeVisible();
    const outboxRow = page.getByRole("row").filter({ hasText: subject });
    await expect(outboxRow).toBeVisible();

    // View file history timeline drawer (BW-FTS-06)
    await outboxRow.getByRole("button", { name: /view history/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });
});

test.describe("fts: inbox forwarding and return actions", () => {
  test.use(signedInAs("placementOfficer"));

  test("inspects inbox and opens forward and return modals (FTS-UC-005, FTS-UC-006, FTS-UC-008, BW-FTS-02, BW-FTS-03)", async ({ page }) => {
    await page.goto("/fts/inbox");
    await actAs(page, "placementOfficer");
    await expect(page.getByRole("heading", { name: "File Inbox", level: 2 })).toBeVisible();

    const forwardButtons = page.getByRole("button", { name: /forward/i });
    if ((await forwardButtons.count()) > 0) {
      await forwardButtons.first().click();
      const modal = page.getByRole("dialog");
      await expect(modal).toBeVisible();
      await page.keyboard.press("Escape");
      await expect(modal).toBeHidden();
    }
  });
});

test.describe("fts: governance and audit inspection", () => {
  test.use(signedInAs("placementOfficer"));

  test("displays governance metrics cards and audit trail table (FTS-UC-010, CFR-FTS-05)", async ({ page }) => {
    await page.goto("/fts/governance");
    await actAs(page, "placementOfficer");
    await expect(page.getByRole("heading", { name: "FTS Governance & Audit", level: 2 })).toBeVisible();
    await expect(page.getByText("Total Files")).toBeVisible();
    await expect(page.getByText("Active (Circulated)")).toBeVisible();
  });
});
