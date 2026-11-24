// InvoicesPage tests: loading, empty, error, permission gate, and invoice recording.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import InvoicesPage from "./InvoicesPage";

describe("InvoicesPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<InvoicesPage />, ["psm.invoice.view"]);
    expect(screen.getByRole("heading", { name: /invoices & payments/i })).toBeInTheDocument();
  });

  it("renders empty state and hides Record invoice without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<InvoicesPage />, ["psm.invoice.view"]);
    await waitFor(() => expect(screen.getByText(/no invoices recorded/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /record invoice/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Invoice error" } } } });
    renderPsmPage(<InvoicesPage />, ["psm.invoice.view"]);
    await waitFor(() => expect(screen.getByText(/invoice error/i)).toBeInTheDocument());
  });

  it("records a vendor invoice through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, invoice_number: "INV-99" } });
    renderPsmPage(<InvoicesPage />, ["psm.invoice.view", "psm.invoice.create"]);
    fireEvent.click(screen.getByRole("button", { name: /record invoice/i }));
    fireEvent.change(await screen.findByLabelText(/invoice number/i), { target: { value: "INV-99" } });
    fireEvent.click(screen.getByRole("button", { name: /save invoice/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/invoices", expect.objectContaining({ invoice_number: "INV-99" })));
  });
});
