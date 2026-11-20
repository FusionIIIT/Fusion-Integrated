import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";
import { openScreen } from "./setup";

test.describe("placement: the placement chairman", () => {
  test.use(signedInAs("placementChairman"));

  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await actAs(page, "placementChairman");
  });

  test("PC-UC-012: the chairman views oversight reports and company engagement", async ({ page }) => {
    await openScreen(page, "Reports");
    await expect(page.getByRole("heading", { name: "Placement Reports", level: 2 })).toBeVisible();
    await expect(page.getByText("By company")).toBeVisible();
    await expect(page.getByText("Trends across seasons")).toBeVisible();
  });

  test("PC-UC-013: the chairman publishes an official announcement", async ({ page }) => {
    const title = uniqueName("E2E internship programme");
    await openScreen(page, "Announcements");
    await page.getByRole("button", { name: "Publish" }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByRole("textbox", { name: "Title" }).fill(title);
    await dialog.getByRole("textbox", { name: "Body" }).fill("Apply by Friday.");
    const sent = page.waitForResponse((r) =>
      r.url().endsWith("/placement/announcements") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: /publish/i }).click();
    expect((await sent).status()).toBe(201);
    await expect(page.getByText(title)).toBeVisible();
  });
});

test.describe("placement: an alumnus", () => {
  test.use(signedInAs("alumnus"));

  test("PC-UC-017: an alumnus reads statistics and sees no active workflow", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "alumnus");
    await openModuleNav(page, "Placement Cell");
    await expect(sidebar(page).getByRole("link", { name: "Placement Records" })).toHaveCount(0);
    await openScreen(page, "Reports");
    await expect(page.getByRole("heading", { name: "Placement Statistics", level: 2 }))
      .toBeVisible();
    await page.goto("/placement/records");
    await expect(page.getByText("Not available to your role")).toBeVisible();
  });
});
