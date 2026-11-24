// StockPage tests: loading, empty, error, permission gate, and item creation action.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import StockPage from "./StockPage";

describe("StockPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<StockPage />, ["psm.stock.view"]);
    expect(screen.getByRole("heading", { name: /stock & internal issues/i })).toBeInTheDocument();
  });

  it("renders empty state and hides write buttons without psm.stock.update", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<StockPage />, ["psm.stock.view"]);
    await waitFor(() => expect(screen.getByText(/no stock balances recorded/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /add stock item/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Stock error" } } } });
    renderPsmPage(<StockPage />, ["psm.stock.view"]);
    await waitFor(() => expect(screen.getByText(/stock error/i)).toBeInTheDocument());
  });

  it("creates a stock item when authorized", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    const postSpy = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1, sku: "SW-1", name: "Switch" } });
    renderPsmPage(<StockPage />, ["psm.stock.view", "psm.stock.update"]);
    fireEvent.click(screen.getByRole("button", { name: /add stock item/i }));
    fireEvent.change(await screen.findByLabelText(/sku/i), { target: { value: "SW-1" } });
    fireEvent.change(screen.getByLabelText(/item name/i), { target: { value: "Switch" } });
    fireEvent.click(screen.getByRole("button", { name: /create item/i }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/psm/stock/items", { sku: "SW-1", name: "Switch" }));
  });
});
