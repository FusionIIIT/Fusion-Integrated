import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InventoryPage from "./InventoryPage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const item = { id: 5, name: "Paracetamol 500mg", unit: "strip", stock_level: "40.00",
  reorder_threshold: "50.00", is_low: true };
const alert = { id: 2, item: 5, item_name: "Paracetamol 500mg", level: "40.00",
  threshold: "50.00", created_at: "2026-11-23T12:00:00Z" };
const page = (rows: unknown[]) => ({ results: rows, next: null, previous: null });

function serve() {
  http.get.mockImplementation((url: string) => Promise.resolve({
    data: url === "/phc/inventory/alerts" ? page([alert]) : page([item]) }));
}

describe("InventoryPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.inventory.view"]);
  });

  listStateTests({ get: http.get, page: () => <InventoryPage />, empty: page([]),
    emptyText: /no inventory items/i });

  it("shows low-stock alerts and hides controls without permission", async () => {
    serve();
    renderPage(<InventoryPage />);
    expect(await screen.findByText(/40.00 left, threshold 50.00/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /adjust stock/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add item/i })).not.toBeInTheDocument();
  });

  it("adjusts stock and shows the server's refusal", async () => {
    state.permissions.add("phc.inventory.update");
    serve();
    http.post.mockRejectedValueOnce(refusal("Only 40.00 in stock, so 60 cannot be deducted."));
    renderPage(<InventoryPage />);
    fireEvent.click(await screen.findByRole("button", { name: /adjust stock/i }));
    fireEvent.change(await screen.findByLabelText(/quantity to add/i),
      { target: { value: "-60" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Only 40.00 in stock, so 60 cannot be deducted."))
      .toBeInTheDocument();
    await waitFor(() => expect(http.post).toHaveBeenCalledWith("/phc/inventory/5/adjust",
      { delta: "-60", reason: "" }));
  });
});
