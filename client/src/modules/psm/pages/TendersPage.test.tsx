// TendersPage tests: loading, empty, error, permission gate, and tender creation.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import TendersPage from "./TendersPage";

describe("TendersPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<TendersPage />, ["psm.tender.view"]);
    expect(screen.getByRole("heading", { name: /^tenders$/i })).toBeInTheDocument();
  });

  it("renders empty state and hides create button without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<TendersPage />, ["psm.tender.view"]);
    await waitFor(() => expect(screen.getByText(/no tenders found/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /new tender/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Tender error" } } } });
    renderPsmPage(<TendersPage />, ["psm.tender.view"]);
    await waitFor(() => expect(screen.getByText(/tender error/i)).toBeInTheDocument());
  });

  it("creates a tender through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, tender_number: "TND-1" } });
    renderPsmPage(<TendersPage />, ["psm.tender.view", "psm.tender.create"]);
    fireEvent.click(screen.getByRole("button", { name: /new tender/i }));
    fireEvent.change(await screen.findByLabelText(/tender title/i), { target: { value: "Server Bid" } });
    fireEvent.change(screen.getByLabelText(/scope/i), { target: { value: "1 server" } });
    fireEvent.change(screen.getByLabelText(/evaluation criteria/i), { target: { value: "L1" } });
    fireEvent.click(screen.getByRole("button", { name: /create tender/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/tenders", expect.objectContaining({ title: "Server Bid" })));
  });
});
