import { stateFile } from "../support/session";
import {
  actAs,
  expect,
  openModuleNav,
  sidebar,
  signedInAs,
  test,
  uniqueName,
} from "../support/test";

test.describe("superadmin: interactive user journeys", () => {
  test.use(signedInAs("superAdmin"));

  test("1. policy governance: super admin supersedes a policy parameter through the modal", async ({ page }) => {
    const uniqueVal = `${Math.floor(100 + (Date.now() % 899))}`;
    const reason = uniqueName("Institute policy adjustment");

    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "System Policies" }).click();
    await expect(page.getByRole("heading", { name: "System Policies", level: 2 })).toBeVisible();

    await expect(page.getByRole("table")).toBeVisible();
    const rowSupersede = page.getByRole("button", { name: "Supersede", exact: true }).first();
    if (await rowSupersede.isVisible()) {
      await rowSupersede.click();
    } else {
      await page.getByRole("button", { name: /supersede parameter/i }).click();
      const keyInput = page.getByRole("dialog").getByRole("textbox", { name: /^Parameter key/i });
      await keyInput.click();
      await page.getByRole("option", { name: "archival.reversibility_window_days" }).click();
    }

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel(/^New value/i).fill(uniqueVal);
    await dialog.getByLabel(/^Reason for change/i).fill(reason);

    const superseded = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/policy/parameters") && r.request().method() === "POST",
    );
    await dialog.getByRole("button", { name: "Supersede", exact: true }).click();
    expect((await superseded).ok()).toBe(true);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: uniqueVal });
    await expect(row).toBeVisible();
  });

  test("2. purge governance: UI dataset archival, dual-auth initiation, it_head approval, and execution", async ({
    page,
    browser,
  }) => {
    const archiveTitle = uniqueName("Expired Departmental Records");
    const purgeReason = uniqueName("Retention period elapsed");

    // Step 1: Create eligible historical dataset archive through the Archival Governance UI
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Archival Governance" }).click();
    await expect(page.getByRole("heading", { name: "Archival Governance", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: /Archive Dataset/i }).click();
    const dsDialog = page.getByRole("dialog");
    await expect(dsDialog).toBeVisible();
    await dsDialog.getByLabel(/^Dataset category/i).fill("compliance");
    await dsDialog.getByLabel(/^Dataset title/i).fill(archiveTitle);
    await dsDialog.getByLabel(/^Date range start/i).fill("2018-01-01");
    await dsDialog.getByLabel(/^Date range end/i).fill("2018-12-31");
    await dsDialog.getByLabel(/^Record count/i).fill("50");
    await dsDialog.getByLabel(/^Backup file path/i).fill("/backups/compliance_2018.tar.gz");
    await dsDialog.getByLabel(/^Backup SHA-256 checksum/i).fill(
      "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
    );
    await dsDialog.getByLabel(/^Retention expires at/i).fill("2020-01-01");

    const dsCreated = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/archival/datasets") && r.request().method() === "POST",
    );
    await dsDialog.getByRole("button", { name: /Confirm Archive Dataset/i }).click();
    const dsRes = await dsCreated;
    expect(dsRes.ok()).toBe(true);
    const archive = await dsRes.json();
    await expect(dsDialog).toBeHidden();
    await expect(page.getByRole("row").filter({ hasText: archiveTitle })).toBeVisible();

    // Step 2: super_admin initiates purge request in Purge Authorization UI
    await sidebar(page).getByRole("link", { name: "Purge Authorization" }).click();
    await expect(page.getByRole("heading", { name: "Purge Authorization", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: /initiate purge/i }).click();
    const initDialog = page.getByRole("dialog");
    await expect(initDialog).toBeVisible();
    await initDialog.getByLabel(/^Dataset Archive ID/i).fill(String(archive.id));
    await initDialog.getByLabel(/^Request reason/i).fill(purgeReason);

    const initiated = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/purge/requests") && r.request().method() === "POST",
    );
    await initDialog.getByRole("button", { name: /create purge request/i }).click();
    expect((await initiated).ok()).toBe(true);
    await expect(initDialog).toBeHidden();

    const purgeRow = page.getByRole("row").filter({ hasText: purgeReason });
    await expect(purgeRow).toBeVisible();
    await expect(purgeRow).toContainText(/pending it head/i);

    // Step 3: it_head account (stf00200) approves the request
    const itContext = await browser.newContext({ storageState: stateFile("itHead") });
    const itPage = await itContext.newPage();
    try {
      await itPage.goto("/superadmin/purge");
      await actAs(itPage, "itHead");
      const itHeadRow = itPage.getByRole("row").filter({ hasText: purgeReason });
      await expect(itHeadRow).toBeVisible();
      await itHeadRow.getByRole("button", { name: "Approve" }).click();

      const decisionDialog = itPage.getByRole("dialog");
      await expect(decisionDialog).toBeVisible();
      await decisionDialog.getByLabel(/^Comments/i).fill("Authorized by IT Head after audit.");

      const approved = itPage.waitForResponse(
        (r) => r.url().includes("/decision/") && r.request().method() === "POST",
      );
      await decisionDialog.getByRole("button", { name: "Approve" }).click();
      expect((await approved).ok()).toBe(true);
      await expect(decisionDialog).toBeHidden();
      await expect(itHeadRow).toContainText(/approved/i);
    } finally {
      await itContext.close();
    }

    // Step 4: super_admin executes the permanent purge
    await page.reload();
    const superAdminRow = page.getByRole("row").filter({ hasText: purgeReason });
    await expect(superAdminRow).toBeVisible();
    await superAdminRow.getByRole("button", { name: "Execute Purge" }).click();

    const execDialog = page.getByRole("dialog");
    await expect(execDialog).toBeVisible();
    const executed = page.waitForResponse(
      (r) => r.url().includes("/execute/") && r.request().method() === "POST",
    );
    await execDialog.getByRole("button", { name: "Confirm Permanent Purge" }).click();
    expect((await executed).ok()).toBe(true);
    await expect(execDialog).toBeHidden();
    await expect(superAdminRow).toContainText(/purged/i);
  });

  test("3. archival governance: super admin archives and restores a user through the UI", async ({ page }) => {
    const uid = Math.floor(20000 + (Date.now() % 50000));
    const uname = `user_${uid}`;

    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Archival Governance" }).click();
    await expect(page.getByRole("heading", { name: "Archival Governance", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: /Archive User/i }).click();
    const archiveDialog = page.getByRole("dialog");
    await expect(archiveDialog).toBeVisible();
    await archiveDialog.getByLabel(/^User ID/i).fill(String(uid));
    await archiveDialog.getByLabel(/^Institute ID/i).fill(`2021BCS${uid}`);
    await archiveDialog.getByLabel(/^Username/i).fill(uname);
    await archiveDialog.getByLabel(/^Institute Email/i).fill(`${uname}@iiitdmj.ac.in`);
    await archiveDialog.getByLabel(/^Archival reason/i).fill("Graduation archival");

    const archived = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/archival/users") && r.request().method() === "POST",
    );
    await archiveDialog.getByRole("button", { name: /Confirm Archive User/i }).click();
    expect((await archived).ok()).toBe(true);
    await expect(archiveDialog).toBeHidden();

    const userRow = page.getByRole("row").filter({ hasText: uname });
    await expect(userRow).toBeVisible();
    await userRow.getByRole("button", { name: /^Restore$/i }).click();

    const restoreDialog = page.getByRole("dialog");
    await expect(restoreDialog).toBeVisible();
    await restoreDialog.getByLabel(/^Restoration reason/i).fill("Rejoining programme as postgraduate.");

    const restored = page.waitForResponse(
      (r) => r.url().includes("/restore/") && r.request().method() === "POST",
    );
    await restoreDialog.getByRole("button", { name: "Confirm Restore" }).click();
    expect((await restored).ok()).toBe(true);
    await expect(restoreDialog).toBeHidden();
    await expect(userRow).toContainText(/restored/i);
  });

  test("4. historical archive lifecycle: create, list, and restore historical dataset archive through UI", async ({
    page,
  }) => {
    const archiveTitle = uniqueName("Historical Semester Records");

    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Archival Governance" }).click();
    await expect(page.getByRole("heading", { name: "Archival Governance", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: /Archive Dataset/i }).click();
    const dsDialog = page.getByRole("dialog");
    await expect(dsDialog).toBeVisible();
    await dsDialog.getByLabel(/^Dataset category/i).fill("academics");
    await dsDialog.getByLabel(/^Dataset title/i).fill(archiveTitle);
    await dsDialog.getByLabel(/^Date range start/i).fill("2019-01-01");
    await dsDialog.getByLabel(/^Date range end/i).fill("2019-12-31");
    await dsDialog.getByLabel(/^Record count/i).fill("120");
    await dsDialog.getByLabel(/^Backup file path/i).fill("/backups/academics_2019.tar.gz");
    await dsDialog.getByLabel(/^Backup SHA-256 checksum/i).fill(
      "b1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
    );
    await dsDialog.getByLabel(/^Retention expires at/i).fill("2028-01-01");

    const created = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/archival/datasets") && r.request().method() === "POST",
    );
    await dsDialog.getByRole("button", { name: /Confirm Archive Dataset/i }).click();
    expect((await created).ok()).toBe(true);
    await expect(dsDialog).toBeHidden();

    const dsRow = page.getByRole("row").filter({ hasText: archiveTitle });
    await expect(dsRow).toBeVisible();
    await expect(dsRow).toContainText(/archived/i);

    const restored = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/archival/history/") && r.url().includes("/restore/"),
    );
    await dsRow.getByRole("button", { name: /Restore Dataset/i }).click();
    expect((await restored).ok()).toBe(true);
    await expect(dsRow).toContainText(/restored/i);
  });

  test("5. compliance audit: super admin filters audit logs by actor username", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Audit Logs" }).click();
    await expect(page.getByRole("heading", { name: "Audit Logs", level: 2 })).toBeVisible();

    const searchInput = page.getByLabel("Search by actor username");
    await expect(searchInput).toBeVisible();

    const filtered = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/audit/logs") && r.url().includes("actor_username=stf00100"),
    );
    await searchInput.fill("stf00100");
    await filtered;

    const table = page.getByRole("table");
    await expect(table).toBeVisible();
    await expect(table.getByRole("row").filter({ hasText: "stf00100" }).first()).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Export CSV" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("audit");
    expect(await download.path()).toBeTruthy();
  });
});
