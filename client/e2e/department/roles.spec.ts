import { expect, signedInAs, test } from "../support/test";
import { ADMIN_ID, ensureTenure, HOD_ID, openDept } from "./helpers";

test.describe("department: role tenures", () => {
  test.use(signedInAs("deptHod"));

  test("UC-DEPT-020/022: the central authority records tenures and the HOD becomes the headship", async ({ page, browser }) => {
    await ensureTenure(browser, "HOD", HOD_ID);
    await ensureTenure(browser, "Dept_Admin", ADMIN_ID);
    await openDept(page, "deptHod", "Overview", "Computer Science and Engineering");
    await expect(page.getByText("No HOD in effect")).toBeHidden();
    await openDept(page, "deptHod", "HOD & Dept_Admin", "HOD & Dept_Admin");
    await expect(page.getByRole("button", { name: "Record tenure" })).toHaveCount(0);
  });
});
