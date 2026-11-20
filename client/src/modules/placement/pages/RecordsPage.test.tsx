/** Placement Records: the five states, and a correction that needs a reason. */
import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { OfficeRecord } from "../api/types";
import RecordsPage from "./RecordsPage";

const hooks = vi.hoisted(() => ({
  useOfficeRecords: vi.fn(),
  useRecordRevisions: vi.fn(),
  useCorrectRecord: vi.fn(),
  useSeasons: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const row: OfficeRecord = {
  id: 7, user_id: 4021, company: { id: 3, name: "Acme" }, season: "2026-27",
  source: "campus", kind: "fte", ctc_lpa: "12.00", is_active: true,
  created_at: "2026-11-02T10:00:00Z", updated_at: "2026-11-02T10:00:00Z",
};
const mutate = vi.fn();

function page() {
  return render(<MantineProvider><RecordsPage /></MantineProvider>);
}

describe("RecordsPage", () => {
  beforeEach(() => {
    mutate.mockReset();
    hooks.useSeasons.mockReturnValue({ data: [{ season: "2026-27" }] });
    hooks.useCorrectRecord.mockReturnValue({ mutate, isPending: false, error: null });
    hooks.useRecordRevisions.mockReturnValue({ data: [], isPending: false, error: null });
    hooks.useOfficeRecords.mockReturnValue(
      { data: { results: [row] }, isPending: false, error: null });
  });

  it("shows a loader while loading", () => {
    hooks.useOfficeRecords.mockReturnValue({ data: undefined, isPending: true, error: null });
    page();
    expect(screen.queryByText("Acme")).not.toBeInTheDocument();
  });

  it("says what an empty list means", () => {
    hooks.useOfficeRecords.mockReturnValue(
      { data: { results: [] }, isPending: false, error: null });
    page();
    expect(screen.getByText("No placement records")).toBeInTheDocument();
  });

  it("renders a real error", () => {
    hooks.useOfficeRecords.mockReturnValue(
      { data: undefined, isPending: false, error: new Error("boom") });
    page();
    expect(screen.queryByText("Placement Records")).not.toBeInTheDocument();
  });

  it("lists records with their package and status", () => {
    page();
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByText("12.00")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("sends a correction only with a reason", () => {
    page();
    fireEvent.click(screen.getByRole("button", { name: "Correct" }));
    const save = screen.getByRole("button", { name: "Save correction" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Reason/), {
      target: { value: "Revised letter." } });
    fireEvent.click(save);
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7, reason: "Revised letter.", kind: "fte" }),
      expect.anything());
  });

  it("opens the correction history", async () => {
    page();
    fireEvent.click(screen.getByRole("button", { name: "History" }));
    expect(await screen.findByText("This record has never been corrected."))
      .toBeInTheDocument();
  });
});
