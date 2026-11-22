// TransfersPage tests: loading, empty, error, permission gate, and transfer request action.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import TransfersPage from "./TransfersPage";

describe("TransfersPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<TransfersPage />, ["psm.transfer.view"]);
    expect(screen.getByRole("heading", { name: /inter-departmental stock transfers/i })).toBeInTheDocument();
  });

  it("renders empty state and hides request button without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<TransfersPage />, ["psm.transfer.view"]);
    await waitFor(() => expect(screen.getByText(/no stock transfers found/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /request transfer/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Transfer error" } } } });
    renderPsmPage(<TransfersPage />, ["psm.transfer.view"]);
    await waitFor(() => expect(screen.getByText(/transfer error/i)).toBeInTheDocument());
  });

  it("submits a transfer request", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, transfer_number: "TRF-1" } });
    renderPsmPage(<TransfersPage />, ["psm.transfer.view", "psm.transfer.create"]);
    fireEvent.click(screen.getByRole("button", { name: /request transfer/i }));
    fireEvent.click(await screen.findByRole("button", { name: /submit request/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/transfers", expect.objectContaining({ item_id: 1 })));
  });
});
