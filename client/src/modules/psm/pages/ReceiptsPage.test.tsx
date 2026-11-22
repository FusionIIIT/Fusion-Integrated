// ReceiptsPage tests: loading, empty, error, permission gate, and GRN recording.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import ReceiptsPage from "./ReceiptsPage";

describe("ReceiptsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<ReceiptsPage />, ["psm.grn.view"]);
    expect(screen.getByRole("heading", { name: /receipts & discrepancies/i })).toBeInTheDocument();
  });

  it("renders empty state and hides Record GRN without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<ReceiptsPage />, ["psm.grn.view"]);
    await waitFor(() => expect(screen.getByText(/no goods receipt notes recorded/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /record grn/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "GRN error" } } } });
    renderPsmPage(<ReceiptsPage />, ["psm.grn.view"]);
    await waitFor(() => expect(screen.getByText(/grn error/i)).toBeInTheDocument());
  });

  it("records a GRN through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, grn_number: "GRN-1" } });
    renderPsmPage(<ReceiptsPage />, ["psm.grn.view", "psm.grn.create"]);
    fireEvent.click(screen.getByRole("button", { name: /record grn/i }));
    fireEvent.click(await screen.findByRole("button", { name: /save grn/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/grns", expect.objectContaining({ purchase_order_id: 1 })));
  });
});
