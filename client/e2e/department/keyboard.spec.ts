import { type Page } from "@playwright/test";

import { expect, signedInAs, test, uniqueName } from "../support/test";

// Step 6.9: one whole flow by keyboard alone, from the sidebar to the saved record. No mouse at all.
async function tabTo(page: Page, name: string, role: string): Promise<void> {
  for (let i = 0; i < 60; i++) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return { role: "", name: "" };
      const label = el.getAttribute("aria-label")
        ?? (el as HTMLInputElement).labels?.[0]?.textContent
        ?? el.textContent ?? "";
      const tag = el.tagName.toLowerCase();
      const kind = tag === "a" ? "link" : tag === "button" ? "button"
        : tag === "textarea" || tag === "input" ? "textbox" : tag;
      return { role: kind, name: label.replace(/\*/g, "").trim() };
    });
    if (focused.role === role && focused.name === name) return;
  }
  throw new Error(`Tab never reached the ${role} "${name}"`);
}

test.describe("department: keyboard only", () => {
  test.use(signedInAs("deptStudent"));

  test("UC-DEPT-007 by keyboard alone: a student reaches Feedback and submits it", async ({ page }) => {
    const subject = uniqueName("Keyboard feedback");
    await page.goto("/");
    await expect(page.getByRole("navigation", { name: "Main navigation" })).toBeVisible();

    const expand = page.getByRole("button", { name: "Expand sidebar" });
    if (await expand.isVisible()) {
      await tabTo(page, "Expand sidebar", "button");
      await page.keyboard.press("Enter");
    }
    const group = page.getByRole("button", { name: "Department" });
    if ((await group.getAttribute("aria-expanded")) !== "true") {
      await tabTo(page, "Department", "button");
      await page.keyboard.press("Enter");
    }
    await tabTo(page, "Feedback", "link");
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Feedback", level: 2 })).toBeVisible();

    await tabTo(page, "Submit feedback", "button");
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await tabTo(page, "Subject", "textbox");
    await page.keyboard.type(subject);
    await tabTo(page, "Feedback", "textbox");
    await page.keyboard.type("Typed without a mouse.");
    await tabTo(page, "Save", "button");
    const saved = page.waitForResponse((r) =>
      r.url().endsWith("/api/v1/department/feedback") && r.request().method() === "POST");
    await page.keyboard.press("Enter");
    expect((await saved).status()).toBe(201);
    await expect(dialog).toBeHidden();
    await expect(page.getByText(subject)).toBeVisible();
  });
});
