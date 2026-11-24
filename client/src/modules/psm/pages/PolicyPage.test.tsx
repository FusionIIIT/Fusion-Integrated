// PolicyPage tests: loading, empty, error, permission gate, and publishing a new policy version.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import PolicyPage from "./PolicyPage";

describe("PolicyPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<PolicyPage />, ["psm.policy.view"]);
    expect(screen.getByRole("heading", { name: /psm policy/i })).toBeInTheDocument();
  });

  it("renders empty state and hides publish button without psm.policy.create", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<PolicyPage />, ["psm.policy.view"]);
    await waitFor(() => expect(screen.getByText(/no psm policy versions published/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /publish new version/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Policy error" } } } });
    renderPsmPage(<PolicyPage />, ["psm.policy.view"]);
    await waitFor(() => expect(screen.getByText(/policy error/i)).toBeInTheDocument());
  });

  it("publishes a new policy version through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 2, version: 2, is_active: true } });
    renderPsmPage(<PolicyPage />, ["psm.policy.view", "psm.policy.create"]);
    fireEvent.click(screen.getByRole("button", { name: /publish new version/i }));
    fireEvent.click(await screen.findByRole("button", { name: /publish policy/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/policy", expect.objectContaining({ direct_limit: "50000.00" })));
  });
});
