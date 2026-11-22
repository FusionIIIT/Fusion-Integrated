import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import InventoryPage from "./InventoryPage";
import { renderPage, testPageStates } from "../testSupport";

describe("InventoryPage", () => {
  testPageStates(InventoryPage, "No inventory items are registered.");

  it("creates a catalogue item with a positive threshold", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 3 } } as never);
    renderPage(InventoryPage);
    await screen.findByText("No inventory items are registered.");
    await user.type(screen.getByLabelText("Item name"), "Gauze");
    await user.clear(screen.getByLabelText("Unit"));
    await user.type(screen.getByLabelText("Unit"), "rolls");
    await user.clear(screen.getByLabelText("Positive reorder threshold"));
    await user.type(screen.getByLabelText("Positive reorder threshold"), "5");
    await user.click(screen.getByRole("button", { name: "Add item" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/inventory", {
      name: "Gauze", unit: "rolls", reorder_threshold: 5,
    }));
  });

  it("hides item creation when the principal lacks inventory.create", async () => {
    renderPage(InventoryPage, ["phc.inventory.view"]);
    await screen.findByText("No inventory items are registered.");
    expect(screen.queryByRole("button", { name: "Add item" })).not.toBeInTheDocument();
  });
});
