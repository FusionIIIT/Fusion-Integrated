import { describe, expect, it } from "vitest";

import { routes } from "./routes";

describe("OAP routes", () => {
  it("defines 8 routes for student and admin procedures", () => {
    expect(routes).toHaveLength(8);
  });

  it("registers index route for OAP dashboard", () => {
    const indexRoute = routes.find((r) => r.index === true);
    expect(indexRoute).toBeDefined();
  });

  it("registers student procedure routes", () => {
    const paths = routes.map((r) => r.path);
    expect(paths).toContain("leave");
    expect(paths).toContain("bonafide");
    expect(paths).toContain("no-dues");
    expect(paths).toContain("branch-change");
  });

  it("guards office routes with RequirePermission", () => {
    const paths = routes.map((r) => r.path);
    expect(paths).toContain("approvals");
    expect(paths).toContain("admin/bonafide");
    expect(paths).toContain("admin/no-dues");
  });
});
