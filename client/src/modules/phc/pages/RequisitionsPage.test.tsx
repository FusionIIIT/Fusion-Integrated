import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import RequisitionsPage from "./RequisitionsPage";
import { renderPage, testPageStates } from "../testSupport";

describe("RequisitionsPage", () => {
  testPageStates(RequisitionsPage, "No requisitions are available.");

  it("submits a requisition for a selected item and quantity", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 15 } } as never);
    renderPage(RequisitionsPage, undefined, "default", {
      "/phc/inventory": { results: [{ id: 5, name: "Gauze", unit: "roll",
        reorder_threshold: 3, is_active: true, stock_quantity: 2 }],
        next: null, previous: null },
    });
    await user.selectOptions(await screen.findByLabelText("Item"), "5");
    await user.clear(screen.getByLabelText("Quantity"));
    await user.type(screen.getByLabelText("Quantity"), "8");
    await user.click(screen.getByRole("button", { name: "Submit requisition" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/requisitions", {
      lines: [{ item_id: 5, quantity: 8 }],
    }));
  });
});
