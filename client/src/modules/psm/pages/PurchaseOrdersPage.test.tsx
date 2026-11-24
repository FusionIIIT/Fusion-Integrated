// PurchaseOrdersPage tests: loading, empty, error, permission gate, and PO issuance.
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import PurchaseOrdersPage from "./PurchaseOrdersPage";

describe("PurchaseOrdersPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<PurchaseOrdersPage />, ["psm.purchase_order.view"]);
    expect(screen.getByRole("heading", { name: /purchase orders/i })).toBeInTheDocument();
  });

  it("renders empty state and hides Issue PO without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<PurchaseOrdersPage />, ["psm.purchase_order.view"]);
    await waitFor(() => expect(screen.getByText(/no purchase orders found/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /issue po/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "PO error" } } } });
    renderPsmPage(<PurchaseOrdersPage />, ["psm.purchase_order.view"]);
    await waitFor(() => expect(screen.getByText(/po error/i)).toBeInTheDocument());
  });

  it("issues a purchase order through the modal", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, po_number: "PO-1" } });
    renderPsmPage(<PurchaseOrdersPage />, ["psm.purchase_order.view", "psm.purchase_order.create"]);
    fireEvent.click(screen.getByRole("button", { name: /issue po/i }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: /issue po/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/purchase-orders", expect.objectContaining({ indent_id: 1 })));
  });
});
