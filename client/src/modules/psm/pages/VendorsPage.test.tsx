// VendorsPage tests: loading, empty, error, permission gate, and vendor onboarding.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import VendorsPage from "./VendorsPage";

describe("VendorsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<VendorsPage />, ["psm.vendor.view"]);
    expect(screen.getByRole("heading", { name: /^vendors$/i })).toBeInTheDocument();
  });

  it("renders empty state and hides onboard button without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<VendorsPage />, ["psm.vendor.view"]);
    await waitFor(() => expect(screen.getByText(/no vendors onboarded yet/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /onboard vendor/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Vendor error" } } } });
    renderPsmPage(<VendorsPage />, ["psm.vendor.view"]);
    await waitFor(() => expect(screen.getByText(/vendor error/i)).toBeInTheDocument());
  });

  it("onboards a vendor through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, name: "Apex Labs" } });
    renderPsmPage(<VendorsPage />, ["psm.vendor.view", "psm.vendor.create"]);
    fireEvent.click(screen.getByRole("button", { name: /onboard vendor/i }));
    fireEvent.change(await screen.findByLabelText(/vendor name/i), { target: { value: "Apex Labs" } });
    fireEvent.click(screen.getByRole("button", { name: /save vendor/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/vendors", expect.objectContaining({ name: "Apex Labs" })));
  });
});
