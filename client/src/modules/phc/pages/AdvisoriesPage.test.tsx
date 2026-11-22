import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AdvisoriesPage from "./AdvisoriesPage";
import { renderPage, testPageStates } from "../testSupport";

describe("AdvisoriesPage", () => {
  testPageStates(AdvisoriesPage, "There are no published health advisories.");

  it("publishes the entered advisory text", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 5 } } as never);
    renderPage(AdvisoriesPage);
    await screen.findByText("There are no published health advisories.");
    await user.type(screen.getByLabelText("Title"), "Clinic hours");
    await user.type(screen.getByLabelText("Advisory"), "The clinic closes at 4 PM.");
    await user.click(screen.getByRole("button", { name: "Publish advisory" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/advisories", {
      title: "Clinic hours", body: "The clinic closes at 4 PM.",
    }));
  });

  it("hides the publish control without the publishing permission", async () => {
    renderPage(AdvisoriesPage, ["phc.advisory.view"]);
    await screen.findByText("There are no published health advisories.");
    expect(screen.queryByRole("button", { name: "Publish advisory" })).not.toBeInTheDocument();
  });
});
