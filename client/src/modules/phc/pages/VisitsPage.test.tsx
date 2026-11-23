import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { allPermissions, renderPage } from "../testSupport";
import VisitsPage from "./VisitsPage";

describe("VisitsPage", () => {
  it("shows directory search loading and empty states", async () => {
    const user = userEvent.setup();
    renderPage(VisitsPage, allPermissions, "pending");
    await user.type(screen.getByRole("searchbox", { name: "Find patient" }), "ab");
    expect(await screen.findByRole("status")).toHaveTextContent(/searching/i);
  });

  it("shows a directory error and no-match empty response", async () => {
    const user = userEvent.setup();
    renderPage(VisitsPage);
    await user.type(screen.getByRole("searchbox", { name: "Find patient" }), "ab");
    expect(await screen.findByText("No directory matches.")).toBeInTheDocument();
  });

  it("shows the directory error message after a failed search", async () => {
    const user = userEvent.setup();
    renderPage(VisitsPage, allPermissions, "error");
    await user.type(screen.getByRole("searchbox", { name: "Find patient" }), "ab");
    expect(await screen.findByRole("alert")).toHaveTextContent(/directory search failed/i);
  });

  it("records a visit and prescription for a selected directory patient", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({
      data: { id: 41 },
    } as never);
    renderPage(VisitsPage, allPermissions, "default", {
      "/phc/directory/patients": [{ user_id: 42, display_name: "Directory Person",
        kind: "faculty" }],
    });
    await user.type(screen.getByRole("searchbox", { name: "Find patient" }), "person");
    await user.click(await screen.findByRole("radio", { name: /directory person/i }));
    fireEvent.change(screen.getByLabelText("Visit date"), { target: { value: "2026-11-23" } });
    await user.type(screen.getByLabelText("Symptoms, diagnosis, and clinical remarks"), "Clinical note");
    await user.type(screen.getByLabelText("Medicines, dosage, and instructions"), "Instructions");
    fireEvent.change(screen.getByLabelText("Prescription issue date"), {
      target: { value: "2026-11-23" },
    });
    await user.click(screen.getByRole("button", { name: "Save visit and prescription" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/visits", {
      patient_user_id: 42, visited_on: "2026-11-23", notes: "Clinical note",
      prescription_details: "Instructions", issued_on: "2026-11-23",
    }));
  });
});
