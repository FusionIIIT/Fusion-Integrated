import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPage } from "../test-utils";
import { PmsGuard } from "./access";

// PMS-AFR-220: the session's union of roles is not enough; the acting role must hold it.
describe("PmsGuard", () => {
  afterEach(() => vi.restoreAllMocks());

  it("refuses when only another held role grants the permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { role: "pms_director",
      permissions: ["pms.review.approve"] } });
    const page = vi.fn(() => <button type="button">New application</button>);
    const Page = page;
    renderPage(<PmsGuard permission="pms.application.create"><Page /></PmsGuard>);
    expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByRole("button")).toBeNull();
    expect(page).not.toHaveBeenCalled();
  });

  it("opens for the acting role that holds it", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { role: "student",
      permissions: ["pms.application.create"] } });
    renderPage(<PmsGuard permission="pms.application.create">
      <button type="button">New application</button></PmsGuard>);
    expect(await screen.findByRole("button", { name: "New application" })).toBeInTheDocument();
  });
});
