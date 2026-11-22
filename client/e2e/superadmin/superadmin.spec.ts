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

    const rowSupersede = page.getByRole("button", { name: "Supersede" }).first();
    if (await rowSupersede.isVisible()) {
      await rowSupersede.click();
    } else {
      await page.getByRole("button", { name: /supersede parameter/i }).click();
      const keyInput = page.getByRole("dialog").getByLabel(/^Parameter key/i);
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
    await dialog.getByRole("button", { name: "Supersede" }).click();
    expect((await superseded).ok()).toBe(true);

    await expect(dialog).toBeHidden();
    const row = page.getByRole("row").filter({ hasText: uniqueVal });
    await expect(row).toBeVisible();
  });

  test("2. purge governance: dual-auth initiation, it_head approval, and super_admin execution", async ({ page }) => {
    // Ensure an eligible dataset archive exists with expired retention
    const archiveTitle = uniqueName("Expired Departmental Records");
    const archiveRes = await page.request.post("/api/v1/superadmin/archival/datasets/", {
      data: {
        dataset_category: "compliance",
        title: archiveTitle,
        date_range_start: "2018-01-01",
        date_range_end: "2018-12-31",
        record_count: 50,
        backup_file_path: "/backups/compliance_2018.tar.gz",
        backup_checksum: "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
        retention_expires_at: "2020-01-01",
      },
    });
    expect(archiveRes.ok()).toBe(true);
    const archive = await archiveRes.json();
    const purgeReason = uniqueName("Retention period elapsed");

    // Phase 1: super_admin initiates purge request
    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
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

    // Phase 2: actAs it_head approves the request
    await actAs(page, "itHead");
    await page.goto("/superadmin/purge");
    const itHeadRow = page.getByRole("row").filter({ hasText: purgeReason });
    await expect(itHeadRow).toBeVisible();
    await itHeadRow.getByRole("button", { name: "Approve" }).click();

    const decisionDialog = page.getByRole("dialog");
    await expect(decisionDialog).toBeVisible();
    await decisionDialog.getByLabel(/^Comments/i).fill("Authorized by IT Head after audit.");

    const approved = page.waitForResponse(
      (r) => r.url().includes("/decision/") && r.request().method() === "POST",
    );
    await decisionDialog.getByRole("button", { name: "Approve" }).click();
    expect((await approved).ok()).toBe(true);
    await expect(decisionDialog).toBeHidden();
    await expect(itHeadRow).toContainText(/approved/i);

    // Phase 3: actAs super_admin executes the permanent purge
    await actAs(page, "superAdmin");
    await page.goto("/superadmin/purge");
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

  test("3. archival governance: super admin restores a reversible archived user", async ({ page }) => {
    // Seed a reversible user
    const uid = Math.floor(20000 + (Date.now() % 50000));
    const uname = `user_${uid}`;
    const userRes = await page.request.post("/api/v1/superadmin/archival/users/", {
      data: {
        user_id: uid,
        institute_id: `INST-${uid}`,
        username: uname,
        email: `${uname}@iiitdmj.ac.in`,
        user_kind: "student",
        is_deactivated: true,
        has_pending_transactions: false,
        archival_reason: "Graduation archival",
      },
    });
    expect(userRes.ok()).toBe(true);

    await page.goto("/");
    await actAs(page, "superAdmin");
    await openModuleNav(page, "System Administration");
    await sidebar(page).getByRole("link", { name: "Archival Governance" }).click();
    await expect(page.getByRole("heading", { name: "Archival Governance", level: 2 })).toBeVisible();

    const userRow = page.getByRole("row").filter({ hasText: uname });
    await expect(userRow).toBeVisible();
    await userRow.getByRole("button", { name: "Restore" }).click();

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

  test("4. compliance audit: super admin filters audit logs by actor username", async ({ page }) => {
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

    const exportResponse = page.waitForResponse(
      (r) => r.url().includes("/api/v1/superadmin/audit/export") && r.status() === 200,
    );
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("link", { name: "Export CSV" }).click();
    expect((await exportResponse).ok()).toBe(true);
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain("audit");
  });
});
