import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import InventoryPage from "./InventoryPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const ITEM = { id: 2, name: "Arduino Uno", unit: "board", current_quantity: 18, updated_at: "2026-11-22" };
const REQ = { id: 11, item: 2, item_name: "Arduino Uno", unit: "board", requester_id: 3001, quantity: 4,
  purpose: "", status: "pending_hod", decided_by: null, decided_at: null, reason: "", issued_by: null,
  issued_at: null, created_at: "2026-11-22" };
const FACULTY = ["department.inventory_item.view", "department.stock_request.view", "department.stock_request.create"];

describe("InventoryPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup(FACULTY, { "/inventory-items": "pending" });
    renderPage(<InventoryPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup(FACULTY, { "/inventory-items": page([]), "/stock-requests": page([]) });
    renderPage(<InventoryPage />);
    expect(await screen.findByText("No inventory items yet")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup(FACULTY, { "/inventory-items": serverError() });
    renderPage(<InventoryPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("gives faculty no approve, issue or receipt controls", async () => {
    setup(FACULTY, { "/inventory-items": page([ITEM]), "/stock-requests": page([REQ]) });
    renderPage(<InventoryPage />);
    await screen.findByText("4 board");
    expect(screen.queryByRole("button", { name: "Approve" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Record receipt" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add item" })).toBeNull();
  });

  it("lets faculty request stock and shows a refusal", async () => {
    setup(FACULTY, { "/inventory-items": page([ITEM]), "/stock-requests": page([]) });
    api.post.mockRejectedValueOnce(serverError("Only 18 in stock.", 422));
    renderPage(<InventoryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Request stock" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("textbox", { name: "Item" })).toHaveValue("Arduino Uno (18 board)");
    fireEvent.click(within(dialog).getByRole("button", { name: "Submit request" }));
    expect(await screen.findByText("Only 18 in stock.")).toBeInTheDocument();
    expect(api.post).toHaveBeenCalledWith("/department/stock-requests", { item: 2, quantity: 1, purpose: "" });
  });

  it("lets the HOD approve a pending request", async () => {
    setup(["department.inventory_item.view", "department.stock_request.view", "department.stock_request.approve",
      "department.stock_movement.view"], { "/inventory-items": page([ITEM]), "/stock-requests": page([REQ]),
      "/stock-movements": page([]) });
    api.post.mockResolvedValue({ data: { ...REQ, status: "approved" } });
    renderPage(<InventoryPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/stock-requests/11/decide",
      { approve: true }));
    expect(screen.getByText("No movements yet.")).toBeInTheDocument();
  });
});
