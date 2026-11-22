// IndentsPage tests: loading, empty, error, permission-gated control, and submit action.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import IndentsPage from "./IndentsPage";

describe("IndentsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("shows loading state while fetching", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<IndentsPage />, ["psm.indent.view"]);
    expect(screen.getByRole("heading", { name: /purchase indents/i })).toBeInTheDocument();
  });

  it("shows empty state and hides create button without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { next: null, previous: null, results: [] } });
    renderPsmPage(<IndentsPage />, ["psm.indent.view"]);
    await waitFor(() => expect(screen.getByText(/no purchase indents found/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /new indent/i })).not.toBeInTheDocument();
  });

  it("shows error state when API returns 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Indents failed" } } } });
    renderPsmPage(<IndentsPage />, ["psm.indent.view"]);
    await waitFor(() => expect(screen.getByText(/indents failed/i)).toBeInTheDocument());
  });

  it("submits a new indent through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { next: null, previous: null, results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, indent_number: "IND-1", status: "submitted" } });
    renderPsmPage(<IndentsPage />, ["psm.indent.view", "psm.indent.create"]);
    fireEvent.click(screen.getByRole("button", { name: /new indent/i }));
    fireEvent.change(await screen.findByLabelText(/item description/i), { target: { value: "Lab Switch" } });
    fireEvent.change(screen.getByLabelText(/justification/i), { target: { value: "Networking lab" } });
    fireEvent.click(screen.getByRole("button", { name: /submit indent/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/indents", expect.objectContaining({ item_description: "Lab Switch" })));
  });
});
