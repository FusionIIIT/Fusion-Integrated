/* Real IAA API smoke test, launched by ops/smoke/test_iaa_browser.py.
 * IAM is a synthetic test double; data and state transitions use PostgreSQL.
 */
const { chromium } = require("playwright");
const assert = require("node:assert/strict");

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.IAA_CHROMIUM || "/usr/bin/chromium",
    headless: true, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const errors = [];
  let page;
  async function login(uid) {
    if (page) { await page.unrouteAll({ behavior: "wait" }); await page.context().close(); }
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    page = await context.newPage();
    page.setDefaultTimeout(12000);
    page.on("pageerror", e => errors.push(String(e)));
    await page.route("**/api/v1/**", async route => {
      const request = route.request();
      const path = new URL(request.url()).pathname + new URL(request.url()).search;
      await route.continue({ url: process.env.IAA_API_ORIGIN + path,
        headers: { ...request.headers(), authorization: `Token iaa-smoke-${uid}` } });
    });
    await page.goto((process.env.IAA_VITE_ORIGIN || "http://127.0.0.1:5173") + "/iaa/workspace");
    await page.getByRole("heading", { name: "Institute Accounts and Audits", exact: true }).waitFor();
  }
  async function openRecord() {
    await page.getByRole("button", { name: "Open record", exact: true }).first().click();
    await page.getByRole("heading", { name: "Action history", exact: true }).waitFor();
  }
  async function act(name, field, value) {
    await page.getByRole("button", { name, exact: true }).click();
    const dialog = page.getByRole("dialog", { name, exact: true });
    await dialog.waitFor();
    if (field) await dialog.getByLabel(field, { exact: false }).fill(value);
    await dialog.getByRole("button", { name: `Confirm ${name.toLowerCase()}`, exact: true }).click();
    await dialog.waitFor({ state: "hidden" });
  }
  try {
    await login(101);
    await page.getByRole("button", { name: "New expense / TA claim", exact: true }).click();
    const editor = page.getByRole("dialog", { name: "New expense or TA claim", exact: true });
    await editor.getByLabel("Request type", { exact: true }).fill("voucher");
    await editor.getByLabel("Department", { exact: true }).fill("CSE");
    await editor.getByLabel("Amount", { exact: true }).fill("100.00");
    await editor.getByLabel("Description / trip purpose", { exact: true }).fill("Synthetic browser workflow");
    await editor.getByLabel("Supporting document links", { exact: true }).fill("https://example.org/browser-evidence.pdf");
    await editor.getByRole("button", { name: "Save draft", exact: true }).click();
    await editor.waitFor({ state: "hidden" });
    await openRecord();
    await act("Submit");
    await page.getByRole("button", { name: "Edit", exact: true }).waitFor({ state: "hidden" });
    await login(102); await openRecord(); await act("Validate", "Remarks", "Documentary and policy checks completed");
    for (const uid of [103, 104, 105]) {
      await login(uid); await openRecord(); await act("Approve", "Remarks", "Reviewed and approved");
    }
    await login(102); await openRecord(); await act("Record", "Reference", "Browser internal completion");
    await page.getByText("Recorded", { exact: true }).first().waitFor();
    await page.getByRole("button", { name: "Record", exact: true }).waitFor({ state: "hidden" });
    if (process.env.IAA_SCREENSHOT) await page.screenshot({ path: process.env.IAA_SCREENSHOT, fullPage: true });
    await page.goto((process.env.IAA_VITE_ORIGIN || "http://127.0.0.1:5173") + "/");
    await page.getByText("Latest notifications · Finance Staff", { exact: true }).waitFor();
    if (process.env.IAA_SCREENSHOT) await page.screenshot({ path: process.env.IAA_SCREENSHOT.replace(".png", "-dashboard.png"), fullPage: true });
    await page.getByRole("button", { name: "Notifications", exact: true }).click();
    await page.getByRole("tab", { name: "Notifications", exact: true }).waitFor();
    assert.equal(await page.getByRole("tab", { name: "Notifications", exact: true }).getAttribute("aria-selected"), "true");
    assert.deepEqual(errors, [], "No browser runtime errors");
    console.log("IAA browser workflow passed: draft, submit, Finance validate, HoD/Dean/Director approve, internal record.");
  } catch (error) {
    if (page) { await page.screenshot({ path: "/tmp/iaa-browser-failure.png", fullPage: true });
      require("node:fs").writeFileSync("/tmp/iaa-browser-failure.html", await page.content()); }
    throw error;
  } finally { if (page && !page.isClosed()) await page.unrouteAll({ behavior: "wait" }); await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
