import { ACCOUNTS } from "../accounts";
import { expect, signedInAs, test } from "../support/test";
import {
  approveClub, asAccount, confirmedClub, establishClub, find, manage, openPage, pick,
} from "./steps";

// Each journey signs in two or three people, so it outlasts the default budget.
test.describe.configure({ timeout: 120_000 });

test.describe("gymkhana: clubs", () => {
  test.use(signedInAs("studentAdmin"));

  test("UC-GYM-001 and UC-GYM-011: a club is created open, then approved", async ({ page, browser }) => {
    const name = await establishClub(page, false);
    await find(page, page.getByRole("row").filter({ hasText: name }));
    await expect(page.getByRole("row").filter({ hasText: name })).toContainText("open");
    await approveClub(page, name);
    await expect(page.getByRole("row").filter({ hasText: name })).toContainText("confirmed");
    await asAccount(browser, "student", async (student) => {
      await openPage(student, "Clubs", "Gymkhana Clubs");
      await find(student, student.getByRole("row").filter({ hasText: name }));
    });
  });
});

test.describe("gymkhana: membership and leadership", () => {
  test.use(signedInAs("student"));

  test("UC-GYM-004 and UC-GYM-005: an application becomes a membership", async ({ page, browser }) => {
    const name = await confirmedClub(browser);
    await page.goto("/");
    await openPage(page, "Clubs", "Gymkhana Clubs");
    const apply = page.getByRole("button", { name: `Apply to ${name}` });
    await find(page, apply);
    await apply.click();
    const form = page.getByRole("dialog");
    await form.getByRole("textbox", { name: /achievements/i }).fill("I build robots");
    await form.getByRole("button", { name: "Submit application" }).click();
    await expect(form).toBeHidden();
    await expect(page.getByRole("row").filter({ hasText: name })).toContainText("Applied");

    await asAccount(browser, "clubHead", async (head) => {
      await manage(head, name, "Applications");
      await head.getByRole("checkbox", { name: "Select row" }).check();
      await head.getByRole("textbox", { name: "Remarks (optional)" }).fill("Welcome");
      await head.getByRole("button", { name: "Approve selected" }).click();
      await expect(head.getByText("1 approved.")).toBeVisible();
    });

    await openPage(page, "My Memberships", "My Club Memberships");
    const row = page.getByRole("row").filter({ hasText: name });
    await find(page, row);
    await expect(row).toContainText("confirmed");
    await expect(row).toContainText("Welcome");
  });

  test("UC-GYM-008: a handover gives the club to its new leaders", async ({ page, browser }) => {
    const name = await confirmedClub(browser);
    await asAccount(browser, "clubHead", async (head) => {
      await manage(head, name, "Leadership");
      await head.getByRole("button", { name: "Change leadership" }).click();
      const form = head.getByRole("dialog");
      await pick(form, "New coordinator", ACCOUNTS.student.username);
      await pick(form, "New co-coordinator", ACCOUNTS.studentAdmin.username);
      await form.getByRole("button", { name: "Replace leaders" }).click();
      await expect(head.getByText(`${name} has new leaders.`)).toBeVisible();
    });
    await manage(page, name, "Applications");
    await expect(page.getByRole("button", { name: "Approve selected" })).toBeVisible();
  });
});
