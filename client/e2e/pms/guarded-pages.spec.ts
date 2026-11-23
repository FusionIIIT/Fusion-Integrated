import { actAs, expect, openModuleNav, sidebar, signedInAs, test } from "../support/test";

// Step 6.4: each office page opened directly by a role without its permission shows nothing to press.
const OFFICE_PAGES = ["reviews", "cases", "assignments", "monitoring", "oversight", "audit",
  "directors", "attorney-panel", "settings"];

test.describe("pms: guarded pages", () => {
  test.use(signedInAs("pmsApplicant"));

  for (const path of OFFICE_PAGES) {
    test(`an applicant who opens /pms/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/pms/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }

  test("an applicant's sidebar shows only applicant screens", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "pmsApplicant");
    await openModuleNav(page, "Patent Management");
    await expect(sidebar(page).getByRole("link", { name: "My Applications" })).toBeVisible();
    await expect(sidebar(page).getByRole("link", { name: "Settings" })).toHaveCount(0);
  });
});

test.describe("pms: guarded pages for a Director", () => {
  test.use(signedInAs("pmsDirector"));

  // One test, so the shared session switches role once rather than racing itself.
  test("a Director who opens an applicant, attorney or office page sees nothing to press",
    async ({ page }) => {
      await page.goto("/");
      await actAs(page, "pmsDirector");
      for (const path of ["applications", "cases", "assignments", "settings"]) {
        await page.goto(`/pms/${path}`);
        await expect(page.getByText("Not available to your role")).toBeVisible();
        await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
      }
    });
});
