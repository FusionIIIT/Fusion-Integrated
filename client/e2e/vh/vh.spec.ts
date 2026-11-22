import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test,
} from "../support/test";

test.describe("vh: visitor hostel", () => {
  test.use(signedInAs("student"));

  test("a student indenter views tariffs and navigates to new booking form", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "student");
    await openModuleNav(page, "Facilities");
    await sidebar(page).getByRole("link", { name: "Tariff Card" }).click();
    await expect(page.getByRole("heading", { name: "Tariff Card", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "New Booking" }).click();
    await expect(page.getByRole("heading", { name: "New Booking Requisition", level: 2 })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Visitor Name" })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Purpose of Visit" })).toBeVisible();
  });
});
